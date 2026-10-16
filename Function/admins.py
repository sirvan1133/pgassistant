from Function.config import PANEL_VERIFY_TLS
from Function.db import *
import requests , json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def DEF_CHANGE_PASSWORD(CHATID, ADMIN_NAME, ADMIN_ROLE_ID, ADMIN_PASSWORD):
    PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (CHATID)
    PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
    URL = f"{PANEL_DOMAIN}/api/admin/{ADMIN_NAME}"
    DATA = {"password": ADMIN_PASSWORD}
    DATA = json.dumps(DATA)
    RESPONCE = requests.put(url=URL, headers=PANEL_TOKEN ,data=DATA , verify=PANEL_VERIFY_TLS)
    if RESPONCE.status_code == 200:
        TEXT = "<b>✅ Admin password is changed.</b>"
    else :
        TEXT = f"<b>❌ I can't change admin password.</b>\n<pre>{str(RESPONCE.text)}</pre>"
    return TEXT

def DEF_CHANGE_ROLE(CHATID, ADMIN_USERNAME, ROLE_ID):
    PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (CHATID)
    PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
    URL = f"{PANEL_DOMAIN}/api/admin/{ADMIN_USERNAME}"
    DATA = {"role_id": int(ROLE_ID)}
    DATA = json.dumps(DATA)
    RESPONCE = requests.put(url=URL, headers=PANEL_TOKEN ,data=DATA , verify=PANEL_VERIFY_TLS)
    if RESPONCE.status_code == 200:
        TEXT = "<b>✅ Admin role is changed.</b>"
    else :
        TEXT = f"<b>❌ I can't change admin role.</b>\n<pre>{str(RESPONCE.text)}</pre>"
    return TEXT

def DEF_DELETE_ADMIN(CHATID,ADMIN_USERNAME) :
    PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (CHATID)
    PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
    URL = f"{PANEL_DOMAIN}/api/admin/{ADMIN_USERNAME}"
    RESPONCE = requests.delete(url=URL, headers=PANEL_TOKEN , verify=PANEL_VERIFY_TLS)
    if RESPONCE.status_code == 204:
        TEXT = "<b>✅ Admin is deleted.</b>"
    else :
        TEXT = f"<b>❌ I can't deleted admin.</b>\n<pre>{str(RESPONCE.text)}</pre>"
    return TEXT

def DEF_ADD_ADMIN(CHATID, ADMIN_USERNAME, ADMIN_PASSWORD, ROLE_ID):
    PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (CHATID)
    PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
    URL = f"{PANEL_DOMAIN}/api/admin"
    DATA = {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD, "role_id": int(ROLE_ID)}
    DATA = json.dumps(DATA)
    RESPONCE = requests.post(url=URL, headers=PANEL_TOKEN ,data=DATA , verify=PANEL_VERIFY_TLS)
    if RESPONCE.status_code == 201:
        TEXT = "<b>✅ Admin is added.</b>"
    else :
        TEXT = f"<b>❌ I can't add admin.</b>\n<pre>{str(RESPONCE.text)}</pre>"
    return TEXT
