#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]>=1.2.0",
# ]
# ///
"""Signal MCP server — wraps signal-cli for Claude Code."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("signal-mcp")

SIGNAL_CLI_BIN = os.environ.get("SIGNAL_CLI_BIN") or "signal-cli"
SIGNAL_ACCOUNT = os.environ.get("SIGNAL_ACCOUNT", "").strip() or None


class SignalCliError(RuntimeError):
    pass


def _resolve_bin() -> str:
    found = shutil.which(SIGNAL_CLI_BIN)
    if not found:
        raise SignalCliError(
            f"signal-cli binary not found (looked for {SIGNAL_CLI_BIN!r}). "
            "Install it (see the signal-setup skill) and/or set SIGNAL_CLI_BIN."
        )
    return found


def _run(
    args: list[str],
    *,
    require_account: bool = True,
    timeout: float | None = 60.0,
    json_output: bool = False,
) -> str:
    bin_path = _resolve_bin()
    cmd: list[str] = [bin_path]
    if json_output:
        cmd += ["-o", "json"]
    if require_account:
        if not SIGNAL_ACCOUNT:
            raise SignalCliError(
                "SIGNAL_ACCOUNT environment variable is not set. "
                "Set it to your registered phone number (e.g. +14155551212)."
            )
        cmd += ["-a", SIGNAL_ACCOUNT]
    cmd += args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SignalCliError(f"signal-cli timed out after {timeout}s") from exc
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise SignalCliError(
            f"signal-cli exited {result.returncode}: {stderr or stdout or '(no output)'}"
        )
    return result.stdout


def _parse_json_lines(stdout: str) -> list[Any]:
    out: list[Any] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _recipient_args(
    *,
    phone: str | None,
    username: str | None,
    group_id: str | None,
    note_to_self: bool,
) -> list[str]:
    if note_to_self:
        return ["--note-to-self"]
    if group_id:
        return ["-g", group_id]
    if username:
        return ["-u", username]
    if phone:
        return [phone]
    raise SignalCliError(
        "Specify exactly one recipient: phone, username, group_id, or note_to_self."
    )


@mcp.tool()
def signal_check_setup() -> dict[str, Any]:
    """Verify signal-cli is installed and an account is configured.

    Returns the binary path, version, configured account, and registered accounts.
    Call this first if anything seems off — most issues surface here.
    """
    info: dict[str, Any] = {
        "binary": shutil.which(SIGNAL_CLI_BIN),
        "configured_account": SIGNAL_ACCOUNT,
        "version": None,
        "registered_accounts": [],
        "ok": False,
    }
    if not info["binary"]:
        info["error"] = (
            f"signal-cli not found on PATH (looked for {SIGNAL_CLI_BIN!r}). "
            "Run the signal-setup skill to install it."
        )
        return info
    try:
        info["version"] = _run(["--version"], require_account=False, timeout=10).strip()
    except SignalCliError as exc:
        info["error"] = str(exc)
        return info
    try:
        accounts_out = _run(["listAccounts"], require_account=False, timeout=15)
        accounts: list[str] = []
        for line in accounts_out.splitlines():
            line = line.strip()
            if line.startswith("Number:"):
                accounts.append(line.split(":", 1)[1].strip())
        info["registered_accounts"] = accounts
    except SignalCliError as exc:
        info["error"] = str(exc)
        return info
    if not SIGNAL_ACCOUNT:
        info["error"] = (
            "SIGNAL_ACCOUNT env var not set. Set it to one of the registered accounts."
        )
        return info
    if SIGNAL_ACCOUNT not in info["registered_accounts"]:
        info["error"] = (
            f"SIGNAL_ACCOUNT={SIGNAL_ACCOUNT!r} is not registered with signal-cli. "
            f"Registered: {info['registered_accounts'] or 'none'}."
        )
        return info
    info["ok"] = True
    return info


@mcp.tool()
def signal_send(
    message: str,
    phone: str | None = None,
    username: str | None = None,
    group_id: str | None = None,
    note_to_self: bool = False,
    attachments: list[str] | None = None,
    quote_timestamp: int | None = None,
    quote_author: str | None = None,
    quote_message: str | None = None,
    edit_timestamp: int | None = None,
    view_once: bool = False,
) -> dict[str, Any]:
    """Send a Signal message to a phone number, username, group, or self.

    Specify exactly one of `phone` (E.164, e.g. +14155551212), `username`
    (Signal username like "alice.42"), `group_id` (base64 group id from
    signal_list_groups), or `note_to_self=True`.

    Optional: list of file paths in `attachments`, a quote (timestamp+author+message)
    to reply-quote a prior message, or `edit_timestamp` to edit a sent message.
    Returns the send timestamp — keep it; you'll need it to react/edit/delete later.
    """
    args = ["send", "-m", message]
    if attachments:
        args.append("-a")
        args.extend(attachments)
    if quote_timestamp is not None:
        args += ["--quote-timestamp", str(quote_timestamp)]
        if quote_author:
            args += ["--quote-author", quote_author]
        if quote_message:
            args += ["--quote-message", quote_message]
    if edit_timestamp is not None:
        args += ["--edit-timestamp", str(edit_timestamp)]
    if view_once:
        args.append("--view-once")
    args += _recipient_args(
        phone=phone, username=username, group_id=group_id, note_to_self=note_to_self
    )
    out = _run(args, json_output=True).strip()
    payload: dict[str, Any] = {"raw": out}
    if out:
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            pass
    return payload


@mcp.tool()
def signal_receive(timeout_seconds: float = 5.0, max_messages: int | None = None) -> dict[str, Any]:
    """Pull pending Signal messages from the server.

    `timeout_seconds` controls how long to wait for new messages before returning
    (the underlying call always drains the queue first). Returns a list of
    envelopes — each may contain a `dataMessage` (text/attachments), `receiptMessage`
    (delivery/read), `typingMessage`, `reactionMessage`, or `syncMessage`.
    Decryption errors surface as envelopes with an `error` field; they're usually
    transient prekey-state issues and the affected message is unrecoverable.
    """
    args = ["receive", "--timeout", str(timeout_seconds)]
    if max_messages is not None:
        args += ["--max-messages", str(max_messages)]
    out = _run(args, json_output=True, timeout=timeout_seconds + 30)
    envelopes = _parse_json_lines(out)
    return {"count": len(envelopes), "envelopes": envelopes}


@mcp.tool()
def signal_send_typing(
    stop: bool = False,
    phone: str | None = None,
    username: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Send a typing-started (or typing-stopped) indicator.

    Pair with signal_send: send typing, wait a realistic interval, send the message,
    then call again with `stop=True` (or just send the message — clients usually clear
    the indicator on receive). NOTE: signal-cli's sendTyping does not accept usernames
    directly; for username-only contacts, look up their UUID via signal_list_contacts
    and pass it as `phone`.
    """
    args = ["sendTyping"]
    if stop:
        args.append("--stop")
    args += _recipient_args(
        phone=phone, username=username, group_id=group_id, note_to_self=False
    )
    _run(args)
    return {"ok": True, "stopped": stop}


@mcp.tool()
def signal_send_receipt(
    target_timestamps: list[int],
    recipient: str,
    receipt_type: Literal["read", "viewed"] = "read",
) -> dict[str, Any]:
    """Send a read or viewed receipt for one or more received messages.

    `recipient` is the sender's phone number or UUID (look up via signal_list_contacts
    if the contact is username-only). `target_timestamps` are the message timestamps
    you're acknowledging (the `timestamp` field on the dataMessage you received).
    """
    if not target_timestamps:
        raise SignalCliError("target_timestamps must not be empty")
    args = ["sendReceipt", "--type", receipt_type, "-t"]
    args += [str(ts) for ts in target_timestamps]
    args.append(recipient)
    _run(args)
    return {"ok": True, "type": receipt_type, "count": len(target_timestamps)}


@mcp.tool()
def signal_send_reaction(
    emoji: str,
    target_author: str,
    target_timestamp: int,
    phone: str | None = None,
    username: str | None = None,
    group_id: str | None = None,
    remove: bool = False,
) -> dict[str, Any]:
    """React to a message with an emoji (or remove a previous reaction).

    `target_author` is the original message author (their phone number or UUID).
    `target_timestamp` is that message's timestamp. Recipient identifies the
    conversation: use the same recipient args as signal_send. For a 1:1 chat the
    target_author and recipient are typically the same person.
    """
    args = ["sendReaction", "-e", emoji, "-a", target_author, "-t", str(target_timestamp)]
    if remove:
        args.append("-r")
    args += _recipient_args(
        phone=phone, username=username, group_id=group_id, note_to_self=False
    )
    _run(args)
    return {"ok": True, "emoji": emoji, "removed": remove}


@mcp.tool()
def signal_remote_delete(
    target_timestamp: int,
    phone: str | None = None,
    username: str | None = None,
    group_id: str | None = None,
    note_to_self: bool = False,
) -> dict[str, Any]:
    """Delete a previously sent message for everyone in the conversation.

    `target_timestamp` is the timestamp returned by signal_send when the message was sent.
    """
    args = ["remoteDelete", "-t", str(target_timestamp)]
    args += _recipient_args(
        phone=phone, username=username, group_id=group_id, note_to_self=note_to_self
    )
    _run(args)
    return {"ok": True}


_CONTACT_FIELDS = (
    ("number", "Number:"),
    ("aci", "ACI:"),
    ("name", "Name:"),
    ("profile_name", "Profile name:"),
    ("username", "Username:"),
    ("color", "Color:"),
    ("blocked", "Blocked:"),
    ("message_expiration", "Message expiration:"),
)


def _parse_contact_line(line: str) -> dict[str, Any]:
    contact: dict[str, Any] = {"raw": line}
    indices: list[tuple[int, str, str]] = []
    for key, label in _CONTACT_FIELDS:
        idx = line.find(label)
        if idx != -1:
            indices.append((idx, key, label))
    indices.sort()
    for i, (start, key, label) in enumerate(indices):
        end = indices[i + 1][0] if i + 1 < len(indices) else len(line)
        value = line[start + len(label):end].strip()
        contact[key] = value or None
    return contact


@mcp.tool()
def signal_list_contacts() -> list[dict[str, Any]]:
    """List known contacts on this account.

    Returns each contact's phone number, UUID, profile name, and username if known.
    Username-only contacts will have no phone — use the UUID for sendTyping/sendReceipt.
    """
    out = _run(["listContacts"], timeout=20)
    contacts: list[dict[str, Any]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("Number:"):
            continue
        contacts.append(_parse_contact_line(line))
    return contacts


@mcp.tool()
def signal_list_groups() -> list[dict[str, Any]]:
    """List groups this account belongs to."""
    out = _run(["listGroups", "-d"], json_output=True, timeout=20)
    parsed = _parse_json_lines(out)
    if len(parsed) == 1 and isinstance(parsed[0], list):
        return parsed[0]
    return parsed


@mcp.tool()
def signal_list_accounts() -> list[str]:
    """List phone numbers registered with the local signal-cli (no account filter)."""
    out = _run(["listAccounts"], require_account=False, timeout=15)
    accounts: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Number:"):
            accounts.append(line.split(":", 1)[1].strip())
    return accounts


@mcp.tool()
def signal_get_user_status(
    phones: list[str] | None = None,
    usernames: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Check whether numbers or usernames are registered Signal users.

    Returns a list of {recipient, number/username, uuid, isRegistered}. Useful before
    attempting to send: unregistered numbers fail with an "Unregistered user" error.
    """
    args = ["getUserStatus"]
    if usernames:
        args.append("--username")
        args.extend(usernames)
    if phones:
        args.extend(phones)
    if not phones and not usernames:
        raise SignalCliError("Provide at least one phone or username to look up.")
    out = _run(args, json_output=True, timeout=30)
    parsed = _parse_json_lines(out)
    if len(parsed) == 1 and isinstance(parsed[0], list):
        return parsed[0]
    return parsed


@mcp.tool()
def signal_update_profile(
    name: str | None = None,
    given_name: str | None = None,
    family_name: str | None = None,
    about: str | None = None,
    about_emoji: str | None = None,
    avatar_path: str | None = None,
    remove_avatar: bool = False,
) -> dict[str, Any]:
    """Update this account's Signal profile.

    `name` is shorthand that maps to --given-name. Use `avatar_path` to set a profile
    picture (file path) or `remove_avatar=True` to clear it.
    """
    args = ["updateProfile"]
    if name and not given_name:
        given_name = name
    if given_name is not None:
        args += ["--given-name", given_name]
    if family_name is not None:
        args += ["--family-name", family_name]
    if about is not None:
        args += ["--about", about]
    if about_emoji is not None:
        args += ["--about-emoji", about_emoji]
    if avatar_path:
        args += ["--avatar", avatar_path]
    if remove_avatar:
        args.append("--remove-avatar")
    if len(args) == 1:
        raise SignalCliError("Nothing to update — provide at least one field.")
    _run(args)
    return {"ok": True}


@mcp.tool()
def signal_join_group(invite_uri: str) -> dict[str, Any]:
    """Join a Signal group via its invite URI (signal.group/#... or sgnl://...)."""
    _run(["joinGroup", "--uri", invite_uri], timeout=60)
    return {"ok": True}


@mcp.tool()
def signal_quit_group(group_id: str, delete: bool = False) -> dict[str, Any]:
    """Leave a Signal group. With `delete=True`, also delete it from local storage."""
    args = ["quitGroup", "-g", group_id]
    if delete:
        args.append("--delete")
    _run(args)
    return {"ok": True}


@mcp.tool()
def signal_block(
    phone: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Block a contact (by phone) or a group (by group id)."""
    args = ["block"]
    if group_id:
        args += ["-g", group_id]
    elif phone:
        args.append(phone)
    else:
        raise SignalCliError("Provide either phone or group_id.")
    _run(args)
    return {"ok": True}


@mcp.tool()
def signal_unblock(
    phone: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Unblock a contact (by phone) or a group (by group id)."""
    args = ["unblock"]
    if group_id:
        args += ["-g", group_id]
    elif phone:
        args.append(phone)
    else:
        raise SignalCliError("Provide either phone or group_id.")
    _run(args)
    return {"ok": True}


@mcp.tool()
def signal_get_attachment(attachment_id: str, recipient: str | None = None, group_id: str | None = None) -> dict[str, Any]:
    """Download an attachment by id from a 1:1 conversation or group.

    `attachment_id` comes from a received envelope's dataMessage.attachments[].id.
    Returns the local path where signal-cli stored the file.
    """
    args = ["getAttachment", "--id", attachment_id]
    if group_id:
        args += ["-g", group_id]
    elif recipient:
        args += ["--recipient", recipient]
    else:
        raise SignalCliError("Provide either recipient or group_id.")
    out = _run(args, timeout=120).strip()
    return {"ok": True, "output": out}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
