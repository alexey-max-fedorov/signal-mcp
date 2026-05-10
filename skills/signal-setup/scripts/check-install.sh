#!/usr/bin/env bash
# Diagnostic: verify signal-cli is installed and an account is registered.
# Use when the MCP server itself is failing to launch (uv/python issues).

set -u

echo "=== signal-mcp install check ==="
echo "PATH=$PATH"
echo

bin="${SIGNAL_CLI_BIN:-signal-cli}"
echo "Looking for binary: $bin"
if ! command -v "$bin" >/dev/null 2>&1; then
  echo "  [MISSING] signal-cli not on PATH (and SIGNAL_CLI_BIN not pointing to it)."
  echo "  → see references/install-platforms.md"
  exit 1
fi
echo "  → $(command -v "$bin")"
echo

echo "Version:"
"$bin" --version 2>&1 | sed 's/^/  /'
echo

echo "Java:"
if command -v java >/dev/null 2>&1; then
  java --version 2>&1 | sed 's/^/  /'
else
  echo "  [WARN] java not on PATH. signal-cli-native builds bundle the runtime; otherwise install JRE 21."
fi
echo

echo "Registered accounts:"
"$bin" listAccounts 2>&1 | grep '^Number:' | sed 's/^/  /' || echo "  (none)"
echo

echo "SIGNAL_ACCOUNT env var: ${SIGNAL_ACCOUNT:-(unset)}"
if [ -z "${SIGNAL_ACCOUNT:-}" ]; then
  echo "  [WARN] not set — MCP server will refuse account-scoped calls."
fi

echo
echo "=== done ==="
