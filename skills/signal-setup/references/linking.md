# Linking signal-cli as a secondary device

Linking attaches signal-cli to an existing Signal account that already lives on a phone (or another primary device). The phone keeps its primary role; signal-cli sends and receives in parallel as a "linked device" — same as Signal Desktop.

This is the **default recommendation** for day-to-day automation. No SMS, no captcha, no impact on the user's existing chats.

## Prerequisites

- Signal is installed and registered on the user's phone.
- The phone is on the same Wi-Fi (helpful but not strictly required) and reachable enough to read the QR.
- Optional: `qrencode` on the host running signal-cli to render the QR locally.

## Flow

### 1. Start linking

```bash
signal-cli link -n "Claude (signal-mcp)"
```

Output is a `sgnl://linkdevice?uuid=...&pub_key=...` URI plus a multi-line ASCII/PNG QR (depending on terminal). The URI is single-use and short-lived (~5 min).

If the QR doesn't render (e.g., headless server), pipe through `qrencode`:

```bash
signal-cli link -n "Claude (signal-mcp)" | grep -m1 '^sgnl://' | qrencode -t ansiutf8
```

Or open the URI on a phone via SSH-pasted browser, etc. Whatever gets the URI in front of the phone's Signal app.

### 2. Scan from the primary phone

On the user's phone:

1. Open Signal.
2. Tap profile icon → **Linked devices** → **Link new device** (or `+` icon).
3. Approve the camera prompt → scan the QR (or paste the URI on platforms that support it).
4. Choose a display name when prompted (this is what Signal will show in the user's Linked Devices list).

Within a few seconds, `signal-cli link` returns and prints the registered phone number, e.g.:

```
Associated number: +14155551212
```

That number is the value for `SIGNAL_ACCOUNT`.

### 3. Initial sync

The first `signal-cli receive` after linking will synchronize contacts, groups, and recent messages from the primary. This can take a minute the first time. After that, normal incremental receive applies.

```bash
signal-cli -a "+14155551212" receive --timeout 30
```

### 4. Wire up the env var

Set `SIGNAL_ACCOUNT=+14155551212` in the user's shell profile and reload Claude Code so the MCP server picks it up.

## Re-linking after data loss

If the host's signal-cli data store was deleted but the phone still has the linked-device entry, the link is now orphaned. Tell the user to:

1. On the phone: Linked Devices → tap the orphan entry → Unlink.
2. Re-run `signal-cli link` from scratch.

## Multiple linked devices

A primary device supports multiple links (Signal Desktop on laptop + signal-cli on a server is fine). Use distinct `-n "<name>"` values so the user can tell them apart in the Linked Devices list.

## Limitations of linked devices

- **Cannot register / change number / unregister.** Those are primary-only operations.
- **Cannot change profile name or avatar** from a linked device — `updateProfile` from signal-cli will work for *your* profile if signal-cli is the primary, but on a linked device it has no effect on the canonical account.
- **Group admin actions are still permitted** if the linked device's account is an admin.
- **Message history before linking is not synced** — only contacts/groups and messages received after the link.

## Troubleshooting

- **"Failed to link device" / `org.whispersystems.libsignal.InvalidKeyException`** — QR was scanned after the URI expired. Re-run `signal-cli link`.
- **Linked but no messages arrive on receive** — first receive performs a long sync; give it 60s. Subsequent calls are fast.
- **Primary phone shows duplicate linked entries** — old failed attempts. Safe to remove from the phone.
