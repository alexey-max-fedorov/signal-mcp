---
name: Signal Messaging Patterns
description: This skill should be used when the user asks to "send a Signal message", "reply on Signal", "react to a Signal message", "edit/delete a sent Signal message", "make Signal feel natural", "check who's on Signal", when handling received Signal envelopes (receipts, typing, reactions, decryption errors), or when an MCP tool returns `Unregistered user`, `IDENTITY_FAILURE`, `InvalidPreKeyException`, or other send/receive errors that aren't setup-related. Covers identifier resolution (phone vs username vs UUID), the receive-and-respond loop, human-feeling typing/receipt timing, sending to groups, attachments, and recovering from common errors.
---

# Signal Messaging Patterns

Practical guidance for using `signal-mcp` tools well. The MCP tool docstrings cover *what* each tool does; this skill covers *how to compose them* and the gotchas you only learn the hard way.

## Recipient identifiers — pick the right one

Signal recipients can be addressed three ways. Different MCP tools accept different ones:

| Identifier | Looks like | Works with `signal_send`? | Works with `signal_send_typing` / `signal_send_receipt`? |
|---|---|---|---|
| **Phone (E.164)** | `+14155551212` | Yes (as `phone=`) | Yes (as `phone=` / `recipient=`) |
| **Username** | `alice.42` | Yes (as `username=`) | **No** — pass UUID via `phone=` instead |
| **UUID (ACI)** | `a1b2c3d4-...-7890abcdef01` | Yes (as `phone=`, despite the name) | Yes (as `phone=` / `recipient=`) |
| **Group ID (base64)** | `Pmpi+EfP...iMwI=` | Yes (as `group_id=`) | Yes (as `group_id=`) |

**Rules of thumb:**

- If the contact has a known phone, use it.
- If they're username-only and you need typing/receipts, look up their UUID via `signal_list_contacts` first, then pass it via `phone=`.
- Group IDs are stable; cache them when scripting multi-message flows.
- Before sending to a brand-new number, call `signal_get_user_status` to confirm `isRegistered: true`. Sending to an unregistered number errors out and is visible to nobody.

See `references/identifiers.md` for an extended table of edge cases (group v1 vs v2, deleted accounts, number changes).

## The send-with-presence pattern

A bare `signal_send` works but feels robotic — especially when Claude is responding to a just-received message. Match human cadence:

1. `signal_send_receipt(target_timestamps=[<their msg ts>], recipient=<their phone or UUID>, receipt_type="read")` — show the user's client a read receipt.
2. *Wait* a beat (2–6s for short replies, longer for substantive ones). Use `time.sleep` in scripts; for MCP-driven turns, the model's natural pause is enough.
3. `signal_send_typing(phone=<...>)` — "typing…"
4. *Wait* again — typically 1s per ~6 characters of the eventual message, capped around 6s.
5. `signal_send(message=..., phone=...)` — the message. The receiving client clears the typing indicator automatically; an explicit stop is rarely needed.

For longer messages or thoughtful replies, occasionally split into two `signal_send` calls with a short pause — humans do this. Don't overdo it; chunked spam reads worse than a single paragraph.

## The receive-respond loop

`signal_receive` returns *all* envelope kinds, not just messages. Filter:

- `dataMessage.message` (string, may be null) — actual text.
- `dataMessage.attachments` — files; download with `signal_get_attachment` using the attachment id.
- `dataMessage.reaction` — someone reacted to a message you sent.
- `dataMessage.remoteDelete.timestamp` — they deleted a message; remove it from your local state.
- `receiptMessage` — delivery / read / viewed; usually informational.
- `typingMessage` — they're typing; safe to ignore unless building UI.
- `syncMessage.sentMessage` — *you* sent a message from another device; mirror it into your view.
- envelopes with `error` field — decryption failures (see "Decryption errors" below).

For a chat-bot loop, poll `signal_receive(timeout_seconds=10)` periodically; signal-cli holds the queue server-side, so a longer interval just batches more envelopes per call.

## Reactions, edits, deletes — keep your timestamps

Every `signal_send` response includes a `timestamp` (ms since epoch). **Save it.** That timestamp is the message's identity and is required for:

- `signal_send_reaction(target_timestamp=...)` — react to *their* message (use the timestamp from their `dataMessage.timestamp`).
- `signal_send` with `edit_timestamp=...` — edit a message you sent.
- `signal_remote_delete(target_timestamp=...)` — delete a message you sent (for everyone).

When reacting to your own message in a 1:1 chat: `target_author` is *your* UUID/phone, but recipient is *theirs*. Group reactions: `target_author` is whoever wrote the message, `group_id` is the group.

## Group sends and management

Groups are addressed by base64 group ID (`group_id=`). Get them via `signal_list_groups` — the response includes member lists, admin info, and invite links. To send a message to a group, only `group_id` and `message` are needed.

Joining a group uses an invite link: `signal_join_group(invite_uri="https://signal.group/#...")`. Quitting: `signal_quit_group(group_id=..., delete=True)` to also wipe local state.

## Attachments

**Sending:** pass absolute file paths in `signal_send(attachments=["/abs/path.png"])`. signal-cli also accepts `data:` URIs (RFC 2397) for inline content — useful for in-memory images.

**Receiving:** `dataMessage.attachments` lists `{id, contentType, filename, size}`. Call `signal_get_attachment(attachment_id=..., recipient=<their phone/UUID>)` to download. The function returns the local path signal-cli stored the file at.

## Profile setup hygiene

Signal warns on every send when no profile name is set ("No profile name set..."). Before sending to anyone new, ensure the account has a profile name: `signal_update_profile(name="Claude")`. This is a primary-device-only operation when linked as secondary.

## Decryption errors

`signal_receive` envelopes occasionally include an `error` field with `InvalidMessageException: invalid PreKey message: decryption failed`. This means the sender's session state diverged from yours (often because one side was offline for long enough that prekey state expired). The affected message is **unrecoverable** — don't keep retrying.

Subsequent messages will succeed once one side sends a fresh message that re-establishes the session. If the user is concerned, ask them to tap the conversation on their phone (which sends a small sync) or send any new message.

## Common errors and recovery

| Error | Cause | Fix |
|---|---|---|
| `Unregistered user "+1..."` | Number not on Signal | `signal_get_user_status` first; suggest username or alternate channel |
| `Config file is in use by another instance` | Another signal-cli process holds the lock | Don't run signal-cli manually while the MCP is running; serialise calls |
| `No profile name set` warning | Profile name missing | `signal_update_profile(name="...")` once |
| `signal-cli not found` | Binary missing or `SIGNAL_CLI_BIN` wrong | invoke the **signal-setup** skill |
| `SIGNAL_ACCOUNT not set` | Plugin env var missing | invoke the **signal-setup** skill, Phase 4 |
| `InvalidPreKeyException` | Stale session | Wait for the next message; can't recover this one |

## Privacy reminders

Signal is end-to-end encrypted; everything the MCP server logs (timestamps, message bodies, contact UUIDs) is on the user's machine. Treat it as private:

- Don't echo full message bodies into chat output unless the user asks.
- Don't paste UUIDs / phone numbers into web searches or pastebins.
- The plugin never transmits credentials anywhere — only signal-cli talks to Signal's servers.

## Additional Resources

### Reference Files

- **`references/identifiers.md`** — deep dive on phone/username/UUID/group resolution, edge cases, group v1 vs v2.
- **`references/etiquette.md`** — timing tables for typing/receipts, conversational pacing, when to chunk vs single-send.
- **`references/troubleshooting.md`** — full error catalogue with diagnosis steps.
