"""Interactive local setup. Does not overwrite an existing database."""
import getpass
from contextlib import closing
import os
from pathlib import Path
import sqlite3


def initialize_database(path, *, chat_id, nickname, username, password, domain, token):
    """Initialize only a new database, with parameterized credential inserts."""
    path = Path(path)
    # Reserve the path atomically so concurrent setup cannot overwrite state.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.executescript("""
                CREATE TABLE bot (chatid INTEGER PRIMARY KEY, token TEXT);
                CREATE TABLE monitoring (chatid INTEGER PRIMARY KEY, status TEXT,
                    check_normal INTEGER, check_error INTEGER);
                CREATE TABLE templates (name TEXT PRIMARY KEY, data INTEGER,
                    date INTEGER, proxies TEXT, inbounds TEXT);
                CREATE TABLE users (chatid INTEGER PRIMARY KEY, role TEXT, name TEXT,
                    username TEXT, password TEXT, domain TEXT, step TEXT);
                CREATE TABLE messages (chatid INTEGER PRIMARY KEY, status TEXT);
            """)
            conn.execute("INSERT INTO bot VALUES (?, ?)", (chat_id, token))
            conn.execute("INSERT INTO monitoring VALUES (?, 'on', 10, 100)", (chat_id,))
            conn.execute("INSERT INTO users VALUES (?, 'boss', ?, ?, ?, ?, 'None')",
                         (chat_id, nickname, username, password, domain.rstrip('/')))
            conn.execute("INSERT INTO messages VALUES (?, 'off')", (chat_id,))
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run setup as root on the deployment server.")
    os.umask(0o077)
    env_path = Path('/etc/holderbot-pasarguard.env')
    if not env_path.exists():
        api_id = int(input('Telegram API ID: ').strip())
        api_hash = getpass.getpass('Telegram API hash: ').strip()
        if api_id <= 0 or len(api_hash) != 32 or any(c not in '0123456789abcdefABCDEF' for c in api_hash):
            raise SystemExit('Invalid Telegram application credentials.')
        with env_path.open('x') as f:
            f.write(f'TELEGRAM_API_ID={api_id}\nTELEGRAM_API_HASH={api_hash}\nPANEL_VERIFY_TLS=true\n')
        env_path.chmod(0o600)
    db = Path('holder.db')
    if db.exists():
        print('Existing holder.db preserved. No account settings were replaced.')
        return
    chat_id = int(input('Owner Telegram numeric chat ID: ').strip())
    nickname = input('Owner nickname: ').strip()
    domain = input('PasarGuard HTTPS URL (including port if needed): ').strip().rstrip('/')
    if not domain.startswith('https://') or any(c.isspace() for c in domain):
        raise SystemExit('Enter a valid HTTPS panel URL.')
    username = input('PasarGuard admin username: ').strip()
    password = getpass.getpass('PasarGuard admin password: ')
    token = getpass.getpass('Telegram bot token: ').strip()
    if not all((nickname, username, password, token)):
        raise SystemExit('Empty credentials are not allowed.')
    initialize_database(db, chat_id=chat_id, nickname=nickname, username=username,
                        password=password, domain=domain, token=token)
    print('Local settings initialized. No credentials were printed.')


if __name__ == '__main__':
    main()
