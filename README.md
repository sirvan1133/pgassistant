# PasarGuard-compatible Holderbot

This branch ports the running Holderbot features to the PasarGuard API. Start with
[the migration/install guide](PASARGUARD_MIGRATION.md) and [the change list](CHANGELOG.md).
Telegram application credentials are no longer embedded in code. Existing databases
and session files must remain private and are not overwritten by setup.

Offline checks (Python 3.12; no panel or Telegram connection):

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The legacy project description and author credits are retained below. For current
installation and rollback instructions, follow the guide linked above.

---

![Example Image](holderbotcover.png)

<p align="center">
  <a href="./README.md">
	English
	</a>
	|
	<a href="./README_ru.md">
	Русский
	</a>
	|
	<a href="./README_fa.md">
	فارسی
	</a>

</p>

# هولدر بات چیه ؟

توسعه دهنده این ربات عرفان عزیز هست که به ما داده لطف داشته گذاشته از نسخه فورک هولدر بات استفاده کنیم



دستورات استفاده از ربات :


## install
```
sudo bash -c "$(curl -sL https://github.com/sirvan1133/holderbot/raw/main/holderbot.sh)"
```
## restart
```
sudo bash -c "$(curl -sL https://github.com/sirvan1133/holderbot/raw/main/restart.sh)"
```
## uninstall
```
sudo bash -c "$(curl -sL https://github.com/sirvan1133/holderbot/raw/main/uninstall.sh)"
```

# برای استفاده notice از اینباند زیر استفاده کنید


```
{
  "tag": "Holderbot",
  "listen": "0.0.0.0",
  "port": 2222,
  "protocol": "shadowsocks",
  "settings": {
    "clients": [],
    "network": "tcp,udp"
  }
}
```
