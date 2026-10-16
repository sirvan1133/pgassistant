from Function.config import PANEL_VERIFY_TLS
from Function.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from pyrogram import *
from Function.db import *
from Function.myfeatures import DEF_RESET_ALERT_STATUS
import time, sqlite3, requests
from datetime import datetime, timezone
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Separate DB so heavy per-user writes never lock holder.db (keeps the bot fast)
RESET_DB = "reset.db"

def init_reset_db():
    conn = sqlite3.connect(RESET_DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""CREATE TABLE IF NOT EXISTS reset_state (
        username TEXT PRIMARY KEY, used_traffic INTEGER )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(reset_state)")}
    if "data_limit" not in columns:
        conn.execute("ALTER TABLE reset_state ADD COLUMN data_limit INTEGER")
    if "owner" not in columns:
        conn.execute("ALTER TABLE reset_state ADD COLUMN owner TEXT")
    if "audit_initialized" not in columns:
        conn.execute("""ALTER TABLE reset_state ADD COLUMN audit_initialized
                        INTEGER NOT NULL DEFAULT 0""")
    conn.execute("""CREATE TABLE IF NOT EXISTS user_change_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        username TEXT NOT NULL,
        owner_before TEXT,
        owner_after TEXT,
        used_before INTEGER,
        data_limit_before INTEGER,
        data_limit_after INTEGER,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_user_change_events_owner_time
                    ON user_change_events(owner_after, created_at)""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_user_change_events_user_time
                    ON user_change_events(username, created_at)""")
    conn.commit()
    conn.close()

init_reset_db()

app = Client(
    "reseter",
    api_id=TELEGRAM_API_ID,
    api_hash=TELEGRAM_API_HASH,
    bot_token=DEF_GET_BOT_TOKEN())


def load_all_states():
    """Read every previous state at once -> dict."""
    conn = sqlite3.connect(RESET_DB)
    c = conn.cursor()
    c.execute("""SELECT username, used_traffic, data_limit, owner,
                        audit_initialized FROM reset_state""")
    rows = c.fetchall()
    conn.close()
    return {u: (t, limit, owner, initialized)
            for u, t, limit, owner, initialized in rows}


def save_all_states(pairs):
    """Replace the whole table with the CURRENT users only, in ONE transaction.
    Any user no longer present in the panel is automatically dropped."""
    conn = sqlite3.connect(RESET_DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("DELETE FROM reset_state")
    conn.executemany(
        """INSERT OR REPLACE INTO reset_state
           (username, used_traffic, data_limit, owner, audit_initialized)
           VALUES (?,?,?,?,1)""",
        pairs)
    conn.commit()
    conn.close()


def save_events(events):
    """Append immutable audit events in one transaction."""
    if not events:
        return
    conn = sqlite3.connect(RESET_DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executemany(
        """INSERT INTO user_change_events
           (event_type, username, owner_before, owner_after, used_before,
            data_limit_before, data_limit_after, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        events)
    conn.commit()
    conn.close()


def get_owner(user):
    admin = user.get("admin")
    if isinstance(admin, dict):
        return admin.get("username") or "?"
    return str(admin) if admin else "?"


def format_quota(value):
    if value is None or value <= 0:
        return "Unlimited"
    return f"{round(value / (1024 ** 3), 2)} GB"


def fetch_all_users(domain, headers):
    out = []
    offset = 0
    limit = 500
    while True:
        url = f"{domain}/api/users?offset={offset}&limit={limit}"
        r = requests.get(url, headers=headers, verify=PANEL_VERIFY_TLS)
        if r.status_code != 200:
            break
        data = r.json()
        batch = data.get("users", []) if isinstance(data, dict) else data
        if not batch:
            break
        out.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return out


with app:
    while True:
        try:
            if DEF_RESET_ALERT_STATUS() != "on":
                time.sleep(60)
                continue

            BOSS_CHATID, NODE_STATUS, CHECK_NORMAL, CHECK_ERROR = DEF_MONITORING_DATA()
            PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA(BOSS_CHATID)
            PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
            if not PANEL_TOKEN:
                time.sleep(30)
                continue

            users = fetch_all_users(PANEL_DOMAIN, PANEL_TOKEN)

            prev_states = load_all_states()
            new_pairs = []
            resets = []
            quota_changes = []
            owner_changes = []
            audit_events = []
            event_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

            for USER in users:
                username = USER.get("username")
                if not username:
                    continue
                used = USER.get("used_traffic") or 0
                data_limit = USER.get("data_limit")
                owner = get_owner(USER)
                new_pairs.append((username, used, data_limit, owner))

                prev = prev_states.get(username)
                if prev is None:
                    continue
                prev_used, prev_limit, prev_owner, audit_initialized = prev

                # NULL values mean this row predates quota/owner auditing. Build
                # the first baseline silently so deployment cannot spam alerts.
                if prev_used > 0 and used < prev_used:
                    resets.append((username, prev_used, data_limit, owner))
                    audit_events.append((
                        "traffic_reset", username, prev_owner, owner, prev_used,
                        prev_limit, data_limit, event_time))

                if audit_initialized and data_limit != prev_limit:
                    quota_changes.append((
                        username, prev_limit, data_limit, prev_owner, owner, used))
                    audit_events.append((
                        "quota_change", username, prev_owner, owner, used,
                        prev_limit, data_limit, event_time))

                if audit_initialized and owner != prev_owner:
                    owner_changes.append((
                        username, prev_owner, owner, data_limit, used))
                    audit_events.append((
                        "owner_change", username, prev_owner, owner, used,
                        prev_limit, data_limit, event_time))

            # Save baseline/state once (batch, separate DB)
            if new_pairs:
                save_all_states(new_pairs)
            save_events(audit_events)

            # Notify resets (usually few)
            for username, prev_used, data_limit, admin_name in resets:
                freed_gb = round(prev_used / (1024 ** 3), 2)
                TEXT = (f"<b>🔄 Traffic reset</b>\n\n"
                        f"<b>👤 User :</b> <code>{username}</code>\n"
                        f"<b>📊 Owner :</b> <code>{admin_name}</code>\n"
                        f"<b>📦 Quota :</b> <code>{format_quota(data_limit)}</code>\n"
                        f"<b>📥 Used before reset :</b> <code>{freed_gb} GB</code>")
                try:
                    app.send_message(chat_id=BOSS_CHATID, text=TEXT,
                                     parse_mode=enums.ParseMode.HTML,
                                     disable_notification=True)
                except Exception:
                    pass

            for username, old_limit, new_limit, old_owner, new_owner, used in quota_changes:
                if old_limit and new_limit:
                    delta = new_limit - old_limit
                    delta_text = f"{delta / (1024 ** 3):+.2f} GB"
                else:
                    delta_text = "N/A (Unlimited changed)"
                owner_line = f"<b>📊 Owner :</b> <code>{new_owner}</code>\n"
                if old_owner != new_owner:
                    owner_line = (f"<b>📊 Owner :</b> <code>{old_owner}</code> → "
                                  f"<code>{new_owner}</code>\n")
                TEXT = (f"<b>📦 Traffic quota changed</b>\n\n"
                        f"<b>👤 User :</b> <code>{username}</code>\n"
                        f"{owner_line}"
                        f"<b>⬅️ Old quota :</b> <code>{format_quota(old_limit)}</code>\n"
                        f"<b>➡️ New quota :</b> <code>{format_quota(new_limit)}</code>\n"
                        f"<b>➕ Change :</b> <code>{delta_text}</code>\n"
                        f"<b>📥 Current usage :</b> <code>{round(used / (1024 ** 3), 2)} GB</code>")
                try:
                    app.send_message(chat_id=BOSS_CHATID, text=TEXT,
                                     parse_mode=enums.ParseMode.HTML,
                                     disable_notification=True)
                except Exception:
                    pass

            for username, old_owner, new_owner, data_limit, used in owner_changes:
                TEXT = (f"<b>👤 User owner changed</b>\n\n"
                        f"<b>👤 User :</b> <code>{username}</code>\n"
                        f"<b>⬅️ Old owner :</b> <code>{old_owner}</code>\n"
                        f"<b>➡️ New owner :</b> <code>{new_owner}</code>\n"
                        f"<b>📦 Quota :</b> <code>{format_quota(data_limit)}</code>\n"
                        f"<b>📥 Current usage :</b> <code>{round(used / (1024 ** 3), 2)} GB</code>")
                try:
                    app.send_message(chat_id=BOSS_CHATID, text=TEXT,
                                     parse_mode=enums.ParseMode.HTML,
                                     disable_notification=True)
                except Exception:
                    pass

            time.sleep(60)

        except Exception as e:
            try:
                app.send_message(chat_id=BOSS_CHATID,
                                 text=f"<b>❌ (Checker) Reseter Error :</b>\n<pre>{str(e)}</pre>",
                                 parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
            time.sleep(60)
