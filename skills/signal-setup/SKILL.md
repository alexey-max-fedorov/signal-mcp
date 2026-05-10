---
name: Signal Setup
description: This skill should be used when the user asks to "set up Signal", "install signal-cli", "register Signal account", "link Signal device", "configure SIGNAL_ACCOUNT", or when an MCP tool returns a `signal-cli not found` / `SIGNAL_ACCOUNT not set` / `unregistered account` error. Walks through installing signal-cli, picking between registering a new number and linking as a secondary device, completing verification, and configuring the plugin's environment variables.
---

# Signal Setup

This skill provisions signal-cli and an account so the `signal-mcp` MCP server can run. It covers four phases: **diagnose**, **install**, **provision an account** (register *or* link), and **configure**. Stop at the first phase that resolves the user's blocker.

## Phase 1 — Diagnose

Before installing anything, call the MCP tool to see exactly what's missing:

```
signal_check_setup()
```

Interpret the returned `error` field:

| Error fragment | What's missing | Jump to |
|---|---|---|
| `signal-cli not found` / `binary` is null | signal-cli is not installed | Phase 2 |
| `SIGNAL_ACCOUNT environment variable is not set` | env var for plugin | Phase 4 |
| `is not registered with signal-cli` | account exists but not provisioned (or wrong number) | Phase 3 |
| `ok: true` | nothing to do | stop |

Run `signal-cli --version` directly only if the MCP tool itself is failing to launch (e.g., `uv` missing). For a one-shot diagnostic that doesn't need the MCP server at all, run `scripts/check-install.sh` from this skill — it prints PATH, signal-cli version, java version, and registered accounts.

Note on PATH: the MCP server inherits PATH from whatever shell launched Claude Code. If `uv` and `signal-cli` work in an interactive terminal but not in the MCP tool, ensure they're on PATH in the launching shell's profile (`~/.zshrc`, `~/.bashrc`), not just in shell rc files.

## Phase 2 — Install signal-cli

signal-cli requires Java 21+. Recommend the platform-native install path; fall back to the tarball when no package exists. See `references/install-platforms.md` for full per-OS detail.

Common one-liners:

- **macOS (Homebrew):** `brew install signal-cli`
- **Debian/Ubuntu (apt + Eclipse Adoptium):** install `temurin-21-jre` then download the official tarball
- **Arch Linux:** `pacman -S signal-cli`
- **Nix/NixOS:** `nix-shell -p signal-cli`
- **Manual / generic Linux:** download release tarball from GitHub, extract under `/opt/signal-cli`, symlink into `/usr/local/bin`

After installing, re-run `signal_check_setup()`. If `signal-cli` exists at a non-PATH location, set `SIGNAL_CLI_BIN` to its absolute path instead of putting it on PATH.

## Phase 3 — Provision an account

Two flows. **Ask the user which they want before running anything destructive.**

### Option A — Link as a secondary device (recommended)

If the user already has Signal on a phone and just wants Claude to send/receive on their behalf, link signal-cli as an additional device. No SMS, no captcha, no 7-day cooldowns. The primary phone stays in charge.

Steps:

1. Run `signal-cli link -n "Claude (signal-mcp)"` — prints a `sgnl://linkdevice?...` URI. With `qrencode` installed, pipe through it for a scannable QR (`signal-cli link -n "..." | qrencode -t ansiutf8`).
2. Open Signal on the user's phone → Settings → Linked Devices → Link New Device → scan the QR (or paste the URI).
3. Wait for `signal-cli` to print the registered phone number; that's the `SIGNAL_ACCOUNT` value for Phase 4.

Detail and troubleshooting in `references/linking.md`.

### Option B — Register a new number (primary device)

Only when the user wants signal-cli to be the primary Signal device for a number — typically a fresh phone number used solely for automation. **This will sign the user out of Signal on their phone** if it's the same number; warn them.

Steps (full transcript and captcha link in `references/registration.md`):

1. `signal-cli -a +<E164> register` — Signal sends an SMS verification code. If rate-limited, ask the user to fetch a captcha token from `https://signalcaptchas.org/registration/generate.html` and re-run with `--captcha "signalcaptcha://..."`.
2. `signal-cli -a +<E164> verify <SMS_CODE>` — completes registration. If a registration lock PIN is required, append `-p <PIN>`.
3. `signal-cli -a +<E164> updateProfile --given-name "<Name>"` — sets the profile name (Signal will warn on send if missing).

## Phase 4 — Configure the plugin

The MCP server reads two env vars:

- `SIGNAL_ACCOUNT` (**required**) — E.164 phone number of the provisioned account, e.g. `+14155551212`.
- `SIGNAL_CLI_BIN` (optional) — absolute path to the binary if it's not on PATH.

Set these in the user's shell profile (`~/.zshrc`, `~/.bashrc`) **and** export in the current shell so the MCP server picks them up on next launch:

```bash
export SIGNAL_ACCOUNT="+14155551212"
```

The plugin's `.mcp.json` already references these via `${SIGNAL_ACCOUNT}` / `${SIGNAL_CLI_BIN}`. Ask the user to restart Claude Code (or reload the plugin) so the MCP server picks up the new environment.

Verify:

```
signal_check_setup()  →  { ok: true, ... }
```

Then run a smoke test by asking the user for a username/number to send "hello" to, and call `signal_send`.

## Decision tree (quick)

```
signal_check_setup
├── binary missing      → Phase 2 (install)
├── account not set     → Phase 4 (env var)
├── account not registered
│   ├── user has phone  → Phase 3A (link as secondary)
│   └── user has bare # → Phase 3B (register primary)
└── ok=true             → done
```

## Common pitfalls

- **signal-cli says "Config file is in use by another instance"** — only one signal-cli process can hold the data store. If the MCP server is running, don't run signal-cli manually at the same time. The MCP server itself spawns signal-cli per call and releases between calls; serial calls are safe.
- **"InvalidMessageException: invalid PreKey message"** — incoming message couldn't be decrypted (sender's session got out of sync). Not a setup problem; the message is unrecoverable but later messages will work. Don't trigger setup flow.
- **Linking finishes but listAccounts is empty** — link sometimes silently fails on slow networks; re-run `signal-cli link` and re-scan.
- **Unregistered phone number** — `signal_get_user_status` returns `isRegistered: false`. Check the username flow or confirm the contact actually has Signal.

## Additional Resources

### Reference Files

- **`references/install-platforms.md`** — full install instructions for macOS, Debian/Ubuntu, RHEL/Fedora, Arch, Nix, and manual tarball.
- **`references/registration.md`** — register-as-primary flow including captcha and PIN handling.
- **`references/linking.md`** — link-as-secondary flow including QR generation and re-link.

### Scripts

- **`scripts/check-install.sh`** — one-shot diagnostic: prints PATH, signal-cli version, java version, registered accounts. Run when the MCP tool is unavailable.
