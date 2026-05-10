# Signal identifiers — full reference

Signal supports several recipient identifier types. Knowing which is which prevents most "I sent the message but it didn't arrive" debugging.

## The four kinds

### Phone number (E.164)

Format: `+<country><number>`, no spaces or dashes. e.g. `+14155551212`, `+447911123456`.

- **Universally accepted** by all signal-cli commands.
- **Sender-visible** — the recipient sees the number unless you've set Signal's "phone number sharing" to nobody.
- **Stable** as long as the user keeps the number registered.

If a user changed their number (Signal supports number changes via `startChangeNumber` / `finishChangeNumber`), the *UUID* is stable but the phone is not. Prefer UUID for long-lived references.

### Username

Format: `<base>.<discriminator>`, e.g. `alice.42`, `bob.1234`. The discriminator (the digits after the dot) makes the username globally unique.

- Set by the user in Signal app → Profile → Username.
- **Cannot be used with**: `sendTyping`, `sendReceipt`, `sendReaction` (recipient param), `sendReceipt`. signal-cli's CLI flags `-u USERNAME` only work for `send` and a handful of other commands. For typing/receipt/reaction calls, look up the UUID first.
- Usernames can be deleted/changed; they're a routing convenience, not an identity.

### UUID (ACI / Account Identifier)

Format: standard UUID v4, e.g. `a1b2c3d4-5e6f-7890-abcd-ef0123456789`.

- **The canonical Signal identity.** Persists across number changes and username changes.
- Accepted by signal-cli wherever a phone number is. In MCP tools, pass it via the `phone=` or `recipient=` parameter — yes, despite the name.
- Visible in: `listContacts` output, `getUserStatus` response, every received envelope's `sourceUuid` field, the `recipientAddress` in `send` responses.

### Group ID

Format: base64-encoded 32-byte identifier, e.g. `Pmpi+EfPWmsxiomLe9Nx2XF9HOE483p6iKiFj65iMwI=`.

- Stable for the life of the group.
- Group v2 is the modern format; v1 is deprecated and will fail on most operations. signal-cli only creates v2.
- For sending: pass via `group_id=`. For typing/receipt in a group: also `group_id=`.

## Resolution flow

Given an unknown contact, resolve in this order:

```
have phone? → use it
have username? → call signal_get_user_status, capture the UUID
have UUID only? → use it (pass via phone= or recipient=)
have nothing → ask the user, or list signal_list_contacts
```

## Edge cases

### Username-only contacts (no phone shared)

Common when users have phone-number sharing set to "nobody". `signal_list_contacts` will show `number: null` for these. Their UUID is your only handle. **Cache the UUID** locally — usernames can change.

### Number changes

Signal users can change their phone number while keeping their account. The UUID survives, the phone doesn't. If a previously-working phone-based send starts failing with "Unregistered user", the user may have changed numbers. Re-resolve via username or UUID.

### Same number, new account (re-registration)

If the user re-registers (new device, no PIN), the **UUID changes**. Old UUID becomes dead. Re-resolve via phone, accept the new UUID.

### Phone formatting

signal-cli normalises some inputs but not all. Always pass strict E.164: `+1...`, no parentheses, no internal spaces. `(415) 555-1212` and `415-555-1212` are not valid.

### Numbers without `+`

Reject. signal-cli treats `14155551212` (no plus) as ambiguous and behavior is version-dependent.

### Note-to-self

Address with `note_to_self=True`. signal-cli silently routes via your own UUID; no recipient field needed.

### Group v1 detection

Old groups appear in `listGroups` with shorter IDs (16 bytes vs 32). Most operations fail with "GroupV1 unsupported". Migrate by recreating the group; signal-cli has no v1→v2 migration tool.

## Identifier visibility (what the recipient sees)

- **Sending to a phone number** — recipient sees your phone if you've shared it; otherwise your username (if any) or "Unknown".
- **Sending to a username** — recipient still sees your phone/username per *your* sharing setting; the username they used to find you isn't shown to them after the first message.
- **Sending in a group** — all members see whatever your sharing settings expose to them.

Reactions and typing indicators are visible to the same recipients as the underlying message would be.
