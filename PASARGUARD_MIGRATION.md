# PasarGuard migration and rollback

Target: the PasarGuard API (not direct writes to the panel database). Regression tests
cover payloads compatible with the deployed PasarGuard v5.4.1; future API revisions
must be checked before upgrading. Offline regression tests were run with Python 3.12.

## Before changing a running bot

1. Make a consistent backup of `holder.db`, `reset.db`, Telegram `*.session*` files,
   local environment settings and the old source. Stop the old workers before the final
   database/session copy; do not copy a live SQLite file without its WAL state.
2. Keep the backup private (directory mode 700, sensitive files 600), outside the Git checkout.
3. Stage the new source separately. Do not run two copies of the same Telegram session
   or reset monitor simultaneously. Do not use the legacy installer to erase the old tree.
4. Read [CHANGELOG.md](CHANGELOG.md), review the API differences and run the offline tests.

## New installation

On a dedicated Ubuntu/Debian host with systemd, obtain and review this repository first.
For a merged release, `sudo bash holderbot.sh` installs to `/root/holderbot-pasarguard`.
For an unmerged PR, check out its branch at that path and use the manual steps below.
The installer will not overwrite an unknown existing installation and does not run
`apt upgrade` or recursively delete old directories.

```bash
cd /root/holderbot-pasarguard
python3 -m venv hold
hold/bin/python -m pip install -r requirements.txt
hold/bin/python setup_pasarguard.py
install -m 644 deploy/holderbot-pasarguard@.service /etc/systemd/system/
install -m 644 deploy/holderbot-pasarguard.target /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now holderbot-pasarguard.target
```

Setup prompts privately for Telegram application credentials, the bot token and panel
admin credentials. Get your own API ID/hash from `https://my.telegram.org`.
Existing `holder.db` is preserved; setup does not replace existing owner or panel settings.
Do not paste real values into source, issues or pull requests.
The local SQLite database contains panel credentials in plaintext. File permissions
restrict access but do not encrypt them; protect the host and all backups accordingly.

## Existing installation

- With the old bot stopped, copy its private databases and session files into the new
  deployment working directory. Remove the old bot's reboot cron entry or disable its
  old service before starting the new target. Do not stop unrelated processes.
- Create `/etc/holderbot-pasarguard.env` using `.env.example` as a template and set mode 600.
  Run `setup_pasarguard.py` to create a missing environment file while preserving the DB.
- The service working directory must match the private state location. The included
  unit assumes `/root/holderbot-pasarguard`; customize it for a different layout.
- Legacy templates continue to map inbound tags to groups. Confirm the selected group
  IDs before creating users. Notice handling requires a group whose only inbound is
  `Holderbot`; the group ID is discovered, not assumed to be 2.
- First start migrates local audit tables. Monitor the first polling cycle before
  relying on quota-change notifications.

## HTTPS settings

`PANEL_VERIFY_TLS=true` is the default. Use a valid panel certificate or a trusted CA.
For an intentionally self-signed panel only, set `PANEL_VERIFY_TLS=false` in the private
environment file. This disables identity verification and is not recommended over an
untrusted network. Do not disable verification to conceal unrelated connection problems.

## Verify and roll back

```bash
systemctl --no-pager status 'holderbot-pasarguard@*'
journalctl -u 'holderbot-pasarguard@*' -n 100 --no-pager
```

Check menu access, group selection, admin roles and Billing with a test account. Create
and reset only explicitly authorized test users; offline tests make no live API calls.

To roll back, stop/disable the new target, restore the old source and the matching private
DB/session backup, then start only the old deployment. Keep the new state backup for
investigation. `uninstall.sh` only stops/disables this bot and preserves recoverable data.
Never upload logs or database backups without first removing private information.
