from Function.config import PANEL_VERIFY_TLS
from Function.db import *
import requests , re
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def DEF_GET_INBOUNDS(CHATID) :
    PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (CHATID)
    PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
    URL = f"{PANEL_DOMAIN}/api/inbounds/details"
    RESPONCE = requests.get(url=URL, headers=PANEL_TOKEN , verify=PANEL_VERIFY_TLS)
    if RESPONCE.status_code == 200:
        RESPONCE_DATA = RESPONCE.json()
        INBOUNDS = {}
        INBOUNDS_ALL = []
        INBOUNDS_SELECT = {}
        for ITEM in RESPONCE_DATA:
            TAG = ITEM.get('tag')
            PROTOCOL = ITEM.get('protocol')
            if TAG and PROTOCOL:
                INBOUNDS.setdefault(PROTOCOL, []).append(ITEM)
                INBOUNDS_ALL.append(TAG)
                INBOUNDS_SELECT[TAG] = TAG != "Holderbot"
    else :
        INBOUNDS = {}
        INBOUNDS_ALL = []
        INBOUNDS_SELECT = {}
    return INBOUNDS , INBOUNDS_ALL ,INBOUNDS_SELECT


def DEF_SELECT_INBOUNDS_AND_PROXIES(INBOUNDS , SELECTS) :
    INBOUNDS_ALL = {}
    PROXIES = {}
    for CATAGORY, ITEMS in INBOUNDS.items():
        TAGS = [ITEM['tag'] for ITEM in ITEMS if SELECTS.get(ITEM['tag'], True)]
        if TAGS:
            INBOUNDS_ALL[CATAGORY] = TAGS
            PROXIES[CATAGORY] = {}
    return INBOUNDS_ALL , PROXIES

def DEF_GET_GROUP_SELECTION(CHATID):
    """Return PasarGuard groups and a safe default selection (Group 1/non-Holderbot)."""
    groups = []
    selected = {}
    for item in DEF_GET_GROUPS(CHATID):
        try:
            group_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        name = str(item.get("name") or f"Group {group_id}")
        inbound_tags = set(item.get("inbound_tags") or [])
        disabled = bool(item.get("is_disabled", False))
        groups.append({"id": group_id, "name": name, "is_disabled": disabled})
        selected[group_id] = not disabled and "Holderbot" not in inbound_tags
    return groups, selected

def DEF_SELECTED_GROUP_IDS(SELECTS):
    return sorted(int(group_id) for group_id, enabled in SELECTS.items() if enabled)

def DEF_GROUP_TEMPLATE_PAYLOAD(GROUP_IDS):
    return {"__group_ids__": sorted(set(int(group_id) for group_id in GROUP_IDS))}

def DEF_CREATE_USER(CHATID , USERNAME , DATA , DATE , PROXIES , INBOUNDS) :
    PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (CHATID)
    PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
    DATA_TO_BYTES = int(float(DATA)*(1024**3))
    DATE_TO_SECOND = int(DATE) * (24*60*60)
    if isinstance(INBOUNDS, dict) and "__group_ids__" in INBOUNDS:
        GROUP_IDS = sorted(set(int(group_id) for group_id in INBOUNDS.get("__group_ids__", [])))
    elif isinstance(INBOUNDS, list):
        GROUP_IDS = sorted(set(int(group_id) for group_id in INBOUNDS))
    else:
        # Backward compatibility for templates saved before the PasarGuard migration.
        GROUP_IDS = DEF_GROUP_IDS_FOR_INBOUNDS(CHATID, INBOUNDS)
    if not GROUP_IDS:
        return "❌<b> I can't create user: no matching PasarGuard group was found.</b>"
    DATA = {
        "username": USERNAME,
        "group_ids": GROUP_IDS,
        "data_limit": DATA_TO_BYTES,
        "data_limit_reset_strategy": "no_reset",
        "status": "on_hold",
        "note": "by holderbot",
        "on_hold_timeout": "2059-11-03T20:30:00",
        "on_hold_expire_duration": DATE_TO_SECOND}
    URL = f"{PANEL_DOMAIN}/api/user"
    POST_DATA = json.dumps(DATA)
    RESPONCE = requests.post(url=URL , headers=PANEL_TOKEN , data=POST_DATA , verify=PANEL_VERIFY_TLS)
    if RESPONCE.status_code in (200, 201) :
        URL = f"{PANEL_DOMAIN}/api/user/{USERNAME}"
        RESPONCE = requests.get(url=URL , headers=PANEL_TOKEN , verify=PANEL_VERIFY_TLS)
        if RESPONCE.status_code == 200 :
            RESPONCE_DATA = json.loads(RESPONCE.text)
            TEXT = DEF_ABSOLUTE_SUBSCRIPTION_URL(PANEL_DOMAIN, RESPONCE_DATA.get("subscription_url"))
        else :
            TEXT = f"❌<b> I can't find user.</b>\n<pre>{RESPONCE.text}</pre>"
    else :
        TEXT = f"❌<b> I can't create user.</b>\n<pre>{RESPONCE.text}</pre>"
    return TEXT


def DEF_USERNAME_STARTER(TEXT, MUCH_NUMBER):
    LETTERS_MATCH = re.sub(r'\d+', '', TEXT)
    DIGIT_MATCH = re.search(r'\d+$', TEXT)
    if DIGIT_MATCH:
        START_NUMBER = int(DIGIT_MATCH.group()) + 1
    else:
        START_NUMBER = 1
    RESULT_LIST = []
    for _ in range(int(MUCH_NUMBER)):
        RESULT_LIST.append(LETTERS_MATCH + str(START_NUMBER))
        START_NUMBER += 1
    return RESULT_LIST

def DEF_SEND_QR_TEXT(USER_SUB , USERNAME , DATA , DATE) :
    TEXT = f"<pre>{USER_SUB}</pre>"
    return TEXT
