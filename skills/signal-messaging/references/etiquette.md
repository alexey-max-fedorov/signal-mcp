# Conversation etiquette and timing

Signal isn't IRC. A bot that sends a 200-char paragraph 80ms after receipt feels alien. These guidelines come from observing how humans actually message and from a few rounds of testing the MCP tools live.

## The "feels human" baseline

Three signals to send before a substantive reply, in order:

1. **Read receipt** (`signal_send_receipt`) — instant; tells the user "I've seen this".
2. **Typing indicator** (`signal_send_typing`) — after a short pause, before the message itself.
3. **The message** (`signal_send`) — after a typing-realistic delay.

You can skip 1 if the conversation has been going for a while (read receipts on every message become noise). You can skip 2 for very short messages ("yeah", "ok", "lol") — humans usually don't trigger typing for one-word replies.

## Timing tables

These are starting points, not hard rules. Adjust to context (urgent vs casual, long vs short message).

### After receiving a message — before sending the read receipt

| Context | Wait |
|---|---|
| Active conversation, < 30s since their message | 0–2s |
| Returning to conversation after several minutes | 0s — instant read |
| Sensitive / long message that needs reading | 3–8s (so you actually "read") |

### After read receipt — before typing indicator

| Context | Wait |
|---|---|
| Quick reply | 1–3s |
| Composing a real response | 3–8s |
| Researching or doing work first | as long as needed; no typing yet |

### After typing indicator — before message

Rough heuristic: 1 second per ~6 characters of the eventual message, capped 1.5–7 seconds.

| Message length | Typing duration |
|---|---|
| 1 word ("yeah") | skip typing |
| 1 short sentence | 1.5–3s |
| 2–3 sentences | 3–5s |
| Paragraph | 5–7s, optionally pause-and-resume |

### Between message chunks (when splitting)

| Pattern | Wait between sends |
|---|---|
| "Hey." → "Just wanted to ask..." | 1–2s |
| "(thinking)" → real answer | 3–6s |
| Quoted reply → follow-up | 2–4s |

## When to skip the dance

- **Mass / broadcast messages** — sending the same intro to multiple recipients. Skip typing/receipts; it's not a real conversation.
- **Group sends to channels you don't actively participate in** — typing indicators feel unnatural in a 100-member group.
- **Automated notifications** ("your build finished", "alert: ...") — be functional, not chatty. Often best with a distinct profile name like "Claude (notifier)".

## Tone adaptation

- Read the user's tone in incoming messages. Match capitalization, emoji density, and message length. A 5-word reply in lowercase is the right answer to a 5-word lowercase question.
- Don't over-emoji. Pick one or two that match the recipient's energy.
- Typos / contractions are signals of casualness. If they write "u" and "rn", don't reply with formal grammar.

## Anti-patterns

- **Read receipt → send → typing → send again.** Backwards. Typing comes *before* the message, not after.
- **`sendTyping` then never sending.** Looks like ghosting. Always follow through, or call `sendTyping(stop=True)` if you change your mind.
- **Sending receipt on every typing indicator.** typingMessage envelopes don't need a receipt; receipts are for dataMessages.
- **Reacting to your own messages with celebratory emoji.** Cringe. Unless asked.

## Example — full natural flow

Received: `{"timestamp": 1700000123456, "sourceUuid": "abc...", "dataMessage": {"message": "yo what's up"}}`

```python
# 1. Mark as read (1s after seeing it)
sleep(1)
signal_send_receipt(target_timestamps=[1700000123456], recipient="abc...", receipt_type="read")

# 2. Pause as if reading
sleep(2)

# 3. Show typing
signal_send_typing(phone="abc...")

# 4. Type-time
sleep(3)

# 5. Reply
signal_send(message="not much, you?", phone="abc...")
```

For multi-message replies, chunk by paragraph or topic, not by sentence.
