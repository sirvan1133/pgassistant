# Changelog

## Unreleased — PasarGuard compatibility (2026-10-16)

### Bot features migrated from the running deployment

- Create users by selecting PasarGuard Groups rather than per-protocol inbound tags.
- Preserve existing templates: legacy inbound selections are mapped to matching groups.
- Do not select disabled groups or notice-only `Holderbot` groups by default.
- Handle `/api/inbounds/details`, paginated admin/node response objects, HTTP 201 creation
  and HTTP 204 deletion, and the PasarGuard node reconnect endpoint.
- Replace legacy Sudo admin controls with selection of PasarGuard `role_id` values.
- Hide the legacy Protocol entry from the main menu; old helpers remain for compatibility.
- Fix Billing pagination and distinguish finite service quotas from unlimited services,
  including legacy unlimited sentinels. Billing remains a service-allocation report,
  **not** a historical invoice for reset operations.
- Persist reset observations in a separate SQLite database, with previous quota and owner.
- Notify quota changes and ownership changes alongside traffic resets; retain local
  `user_change_events` history, with UTC observation timestamps.
- Migrate old reset-state tables without emitting quota/owner alerts for the initial baseline.
- Resolve relative subscription URLs and use systemd journal output for the Help log export.

### Packaging and privacy

- No deployed databases, Telegram sessions, bot tokens, admin passwords, production
  domains/IPs, or Telegram application credentials are included in the new source.
- Read `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from a root-only environment file.
- Verify panel HTTPS certificates by default; explicit opt-out is documented for
  intentionally self-signed installations.
- Add dependency declarations, environment examples, systemd startup for all five
  components, and a restrictive file-creation umask.
- Replace destructive installation/restart/uninstall behavior: preserve state, use
  parameterized setup SQL, and do not kill unrelated Python processes.
- Add offline regression tests and documented verification commands.

### Important limitations

- Reset/quota/owner notifications are polling observations, not server-side audit events.
  They cannot identify the admin who clicked a button; the displayed admin is the owner.
- Changes occurring entirely between polls can be missed. A lower usage counter is
  treated as a reset and may also reflect scheduled resets or other counter changes.
- Hidden legacy Protocol functions are not advertised as PasarGuard-compatible.
- Some inherited API calls still lack explicit timeouts; this PR does not claim to solve
  every performance or availability issue.
- Nothing in this pull request automatically updates or restarts a live deployment.
