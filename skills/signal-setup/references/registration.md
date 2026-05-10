# Registering signal-cli as the primary device

Use this flow only when the user wants signal-cli to **own** the Signal account for a given phone number. Registering replaces any prior primary device, so a phone with the same number will be signed out.

Prefer the linking flow (`references/linking.md`) for normal day-to-day automation.

## When registration is the right choice

- The user has a **dedicated** phone number for automation (Twilio, Google Voice, second SIM).
- The user explicitly wants Claude / signal-cli to be the *only* device on this number.
- The number has never been registered with Signal, or the user is fine with re-registering and losing existing chats on it.

If any of those is unclear, ask before proceeding.

## Step 1 — Request a verification code

```bash
signal-cli -a "+14155551212" register
```

Signal sends an SMS to the number. Possible responses:

- **Success** — silent exit; the SMS arrives within ~30s.
- **`CaptchaRequiredException`** / 402 / 428 — Signal requires a captcha. Open https://signalcaptchas.org/registration/generate.html in a browser, solve the captcha, and copy the `signalcaptcha://<token>` URI by right-clicking the "Open Signal" link → Copy Link. Then:

  ```bash
  signal-cli -a "+14155551212" register --captcha "signalcaptcha://<token>"
  ```

- **Rate limit / 413** — wait the indicated retry window before re-trying.
- **Voice call fallback** — pass `--voice` to receive the code by phone call instead.

## Step 2 — Verify

When the SMS arrives, complete registration:

```bash
signal-cli -a "+14155551212" verify 123456
```

If a registration lock PIN is set on the account (Signal forces this if the number was previously registered with a PIN), append `-p <PIN>`:

```bash
signal-cli -a "+14155551212" verify 123456 -p 1234
```

## Step 3 — Set a profile name (recommended)

Signal warns on every send when no profile name is set. Set one immediately:

```bash
signal-cli -a "+14155551212" updateProfile --given-name "Claude"
```

Optional: also set `--family-name`, `--about`, `--about-emoji`, `--avatar /path/to/picture.png`.

## Step 4 — Confirm

```bash
signal-cli listAccounts
# → Number: +14155551212
```

Set `SIGNAL_ACCOUNT=+14155551212` in the user's shell as described in the main skill.

## Re-registration

If the user lost access to the local data store but still has the number:

```bash
signal-cli -a "+14155551212" register --reregister
```

This requests a new SMS code without invalidating the registration lock PIN.

## Pitfalls

- **The user's iPhone signed out of Signal.** Expected — the number can only be registered to one primary at a time. Warn before running `register` if there's any chance the phone number is in active use.
- **No SMS arriving.** Signal sometimes sends voice instead silently; check call history. Also try `--voice`.
- **Captcha "Open Signal" link is missing.** Update the browser; the captcha page sometimes fails to render the deep-link button. Refresh and retry.
- **Account already registered on this device.** If `listAccounts` already shows the number, registration was already done — skip to Step 3 / Step 4.
