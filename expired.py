from Function.config import PANEL_VERIFY_TLS
from Function.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from pyrogram import *
from Function.db import *
import time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
app = Client(
    "expired",
    api_id=TELEGRAM_API_ID,
    api_hash=TELEGRAM_API_HASH,
    bot_token=DEF_GET_BOT_TOKEN())

with app :
    while True :
        try :
            BOSS_CHATID , STATUS = DEF_MESSAGER_IMPORT_DATA()
            if STATUS == "on":
                PANEL_USER, PANEL_PASS, PANEL_DOMAIN = DEF_IMPORT_DATA (BOSS_CHATID)
                PANEL_TOKEN = DEF_PANEL_ACCESS(PANEL_USER, PANEL_PASS, PANEL_DOMAIN)
                URL = f"{PANEL_DOMAIN}/api/users?status=expired"
                RESPONCE = requests.get(url=URL , headers=PANEL_TOKEN , verify=PANEL_VERIFY_TLS )

                if RESPONCE.status_code == 200 :
                    RESPONCE_DATA = RESPONCE.json()
                    HOLDERBOT_GROUP_ID = DEF_HOLDERBOT_GROUP_ID(BOSS_CHATID)
                    for USER in RESPONCE_DATA["users"] :
                        if HOLDERBOT_GROUP_ID and USER.get("group_ids") != [HOLDERBOT_GROUP_ID] :
                            USERNAME = USER["username"]
                            URL = f"{PANEL_DOMAIN}/api/user/{USERNAME}"
                            DATA = {"group_ids": [HOLDERBOT_GROUP_ID]}
                            RESPONCE = requests.put(url=URL , json=DATA , headers=PANEL_TOKEN , verify=PANEL_VERIFY_TLS)
                            if RESPONCE.status_code == 200 :
                                app.send_message(chat_id=BOSS_CHATID , text=f"<b>✅ (Checker) Boss! user <code>{USERNAME}</code> is expired,\nI have set the messages.</b>" , parse_mode=enums.ParseMode.HTML , disable_notification=True)
                                time.sleep(0.1)
                            else :
                                app.send_message(chat_id=BOSS_CHATID , text=f"<b>❗ (Checker) Boss! user <code>{USERNAME}</code> is expired,\nbut I can't set the messages.\n\n<pre>{RESPONCE.text}</pre></b>" , parse_mode=enums.ParseMode.HTML , disable_notification=True)
                time.sleep(5)
            else :
                time.sleep(60)
        except Exception as e :
            app.send_message(chat_id=BOSS_CHATID , text=f"<b>❌ (Checker) Expirider Error :</b>\n<pre>{str(e)}</pre>" , parse_mode=enums.ParseMode.HTML)
            time.sleep(60)
            pass
