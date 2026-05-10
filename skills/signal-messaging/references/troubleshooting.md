# Troubleshooting reference

Catalog of errors observed when using `signal-mcp`. Look up the symptom, follow the diagnosis, apply the fix.

## Send-side errors

### `Unregistered user "+1..."` / `Unregistered user`

**Cause:** Recipient phone number is not registered with Signal.

**Diagnosis:** `signal_get_user_status(phones=["+1..."])` → confirms `isRegistered: false`.

**Fix:** None on Signal. Try the user's username (`signal_get_user_status(usernames=[...])`). If still not on Signal, switch to a different channel and tell the user.

### `Failed to send (some) messages`

**Cause:** Aggregate failure across multiple recipients. Only some failed.

**Diagnosis:** Look at the JSON output's `results` array — each entry has `type` (SUCCESS, NETWORK_FAILURE, IDENTITY_FAILURE, UNREGISTERED).

**Fix per type:**
- `IDENTITY_FAILURE` — recipient's safety number changed. Run `signal-cli trust <recipient> -a` to trust on first use, or have the user verify out-of-band first.
- `NETWORK_FAILURE` — transient. Retry.
- `UNREGISTERED` — see above.

### `No profile name set` (warning, not error)

**Cause:** Account has no profile name. Signal warns on every send.

**Fix:** `signal_update_profile(name="...")` once. If linked as secondary device, set on the primary instead.

### Send appears successful but recipient receives nothing

**Causes (in order of likelihood):**
1. Recipient blocked you. No delivery, no error. Try a different number.
2. Recipient's account is registered but their device is offline. Signal will deliver when they next come online — wait.
3. You're sending to a UUID that has been recycled (rare). Re-resolve via phone.

## Receive-side errors

### `InvalidMessageException: invalid PreKey message: decryption failed`

**Cause:** Sender's session state is out of sync with yours. Common after long offline periods.

**Diagnosis:** Envelope appears in `signal_receive` output with `error` field.

**Fix:** **None for that specific message** — it's unrecoverable. Future messages will work after the session re-establishes (which happens automatically on the next send from either side).

### Receive returns no messages but the user says they sent one

**Cause:** Either the message hasn't arrived at Signal's servers yet, or it was already delivered to a different signal-cli process.

**Diagnosis:** `signal_check_setup()` to confirm only one signal-cli holding the lock.

**Fix:** Wait 10–30s, retry `signal_receive(timeout_seconds=15)`. signal-cli is the only consumer of the queue from your account, so missed messages stay queued.

### Envelope with `dataMessage.message: null` and no attachments

**Cause:** Probably a typing indicator (the envelope has `typingMessage` instead) misread, or a message that was edited and then remote-deleted before arriving.

**Fix:** Check for `typingMessage`, `receiptMessage`, `reactionMessage`, `syncMessage` fields — those are non-text envelopes. Ignore if not handling.

## Configuration errors

### `signal-cli not found (looked for 'signal-cli')`

**Cause:** Binary not on PATH and `SIGNAL_CLI_BIN` unset.

**Fix:** Run `signal-setup` skill, Phase 2.

### `SIGNAL_ACCOUNT environment variable is not set`

**Cause:** `.mcp.json` interpolates `${SIGNAL_ACCOUNT}` but the env var is empty.

**Fix:** Set in shell profile, restart Claude Code so the MCP server inherits it. Phase 4 of setup skill.

### `is not registered with signal-cli. Registered: ['+...']`

**Cause:** `SIGNAL_ACCOUNT` doesn't match any registered account.

**Fix:** Either fix the env var to match, or register/link the account that *is* expected. Phase 3 of setup skill.

### `Config file is in use by another instance, waiting…`

**Cause:** Another signal-cli process holds the data store lock. Common when manual signal-cli is run while the MCP server is also running, or two parallel MCP tool calls landed simultaneously.

**Fix:** Serialize calls. The MCP server itself spawns one signal-cli per call and releases the lock between calls; back-to-back calls are fine, but parallel calls aren't. signal-cli will wait briefly, so transient appearances of this message are harmless.

## Linking errors

### Linking succeeded but `listAccounts` shows nothing

**Cause:** Sometimes the `link` command exits zero on slow networks before fully writing the account file.

**Fix:** Re-run `signal-cli link` and re-scan; the orphan device entry can be removed from the phone's Linked Devices list.

### Linked device shows in phone but signal-cli can't receive

**Cause:** First-receive sync hasn't completed. Initial sync takes up to a minute.

**Fix:** Run `signal_receive(timeout_seconds=60)` once and let it complete. Subsequent receives are fast.

## Group errors

### `GroupV1 unsupported` / `Group is GroupV1`

**Cause:** Old (pre-2020) group format. signal-cli only supports v2.

**Fix:** Recreate the group as v2 (any modern Signal client recreates as v2 by default). No automated migration.

### `You are not a member of this group`

**Cause:** Either you've been removed, or the local group cache is stale.

**Fix:** `signal_list_groups()` to refresh. If you're truly removed, ask for re-invite. If the group requires admin approval to join, use `joinGroup` with the invite URI.

## Quick triage flow

```
something broke
├── tool call failed?
│   ├── error mentions "signal-cli" or "SIGNAL_ACCOUNT" → setup skill
│   ├── error mentions "Unregistered" → recipient not on Signal
│   ├── error mentions "InvalidMessage" / "PreKey" → unrecoverable, move on
│   └── error mentions "Config file is in use" → serialise calls, retry
├── tool call succeeded but result is wrong?
│   ├── send timestamp present but recipient saw nothing → likely blocked
│   └── receive empty but messages expected → wait + retry
└── confused? → call signal_check_setup() and start there
```
