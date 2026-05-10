# signal-mcp

A Claude Code plugin for Signal Messenger via [signal-cli](https://github.com/AsamK/signal-cli).

Bundles:
- **MCP server** (`signal-mcp`) wrapping signal-cli with tools for sending, receiving, reactions, typing indicators, receipts, contacts, groups, and profile management.
- **`signal-setup` skill** that walks through installing signal-cli and provisioning an account (link as secondary device or register a new number).
- **`signal-messaging` skill** covering identifier resolution, conversation pacing, error recovery, and the full envelope lifecycle.

## Install

This plugin is distributed as a Claude Code marketplace at this repo. Add it as a marketplace and install:

```
/plugin marketplace add alexey-max-fedorov/signal-mcp
/plugin install signal-mcp
```

(Or clone the repo and load locally.)

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — used to run the Python MCP server with no global install (deps declared inline via PEP 723).
- `signal-cli` — installed via the bundled `signal-setup` skill, or manually beforehand.
- A Signal account — either already on a phone (link signal-cli as secondary, recommended) or a fresh number to register.

### Configure

Two env vars:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SIGNAL_ACCOUNT` | yes | — | E.164 phone number of the registered account, e.g. `+14155551212` |
| `SIGNAL_CLI_BIN` | no | `signal-cli` | Absolute path if signal-cli isn't on PATH |

Set in your shell profile and restart Claude Code so the MCP server picks them up.

## Tools exposed

The MCP server registers these tools (Claude Code prefixes them; see them in `/mcp` after install):

| Tool | Purpose |
|---|---|
| `signal_check_setup` | Verify install + account before doing anything else |
| `signal_send` | Send text/attachments to phone, username, group, or self |
| `signal_receive` | Pull pending envelopes from the server |
| `signal_send_typing` | Start/stop typing indicators |
| `signal_send_receipt` | Send read or viewed receipts |
| `signal_send_reaction` | Emoji-react to a message |
| `signal_remote_delete` | Delete a sent message for everyone |
| `signal_list_contacts` | List known contacts (phone, UUID, profile name, username) |
| `signal_list_groups` | List groups with members and invite links |
| `signal_list_accounts` | List signal-cli's registered accounts |
| `signal_get_user_status` | Check whether a phone/username is on Signal |
| `signal_update_profile` | Set name, about, avatar |
| `signal_join_group` | Join via invite URI |
| `signal_quit_group` | Leave a group |
| `signal_block` / `signal_unblock` | Block / unblock a contact or group |
| `signal_get_attachment` | Download an attachment by id |

## Skills

Skills auto-trigger on relevant phrases:

- **signal-setup** activates on phrases like *"set up Signal"*, *"install signal-cli"*, *"link Signal device"*, or any setup-related error from the MCP server.
- **signal-messaging** activates on *"send a Signal message"*, *"react to..."*, *"reply on Signal"*, or while interpreting received envelopes.

Both skills include reference docs (install per platform, registration, linking, identifiers, etiquette, troubleshooting) loaded on-demand.

## Project layout

```
.
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .mcp.json
├── mcp/
│   └── signal-mcp/
│       └── server.py          # PEP 723 inline-deps Python script
├── skills/
│   ├── signal-setup/
│   │   ├── SKILL.md
│   │   ├── references/        # install-platforms, registration, linking
│   │   └── scripts/           # check-install.sh
│   └── signal-messaging/
│       ├── SKILL.md
│       └── references/        # identifiers, etiquette, troubleshooting
├── LICENSE
└── README.md
```

## Privacy & trust

End-to-end encryption is enforced by Signal itself; this plugin doesn't change that. The MCP server runs locally, talks to signal-cli locally, and signal-cli talks to Signal's servers directly. No third party sees message content. Logs and data live under `~/.local/share/signal-cli/`.

A few things to keep in mind when wiring this up to an autonomous assistant:

- **`signal_send` can attach any local file readable by the user**. A prompt-injected agent could exfiltrate `~/.ssh/id_rsa` or similar via a Signal attachment. Restrict tool permissions in Claude Code (`/permissions`) accordingly, and require human-in-the-loop confirmation for `signal_send` if running autonomously.
- **Tool error messages may include phone numbers, UUIDs, and group IDs** as signal-cli's stderr. Treat conversation transcripts as containing PII when sharing for debugging.
- **The plugin trusts the host environment.** `SIGNAL_CLI_BIN` overrides which binary runs; don't set it to anything you don't trust.

## License

[Signal MCP License](LICENSE) — noncommercial use only. See LICENSE for full terms. For commercial licensing contact alexey.max.fedorov@gmail.com.
