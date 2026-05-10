# Installing signal-cli per platform

signal-cli is a JVM application maintained by AsamK. Java 21+ is required. Installation methods vary; pick by platform. After install, run `signal-cli --version` and `which signal-cli` to confirm.

## macOS — Homebrew (recommended)

```bash
brew install signal-cli
```

This pulls a JRE bundle so no separate Java install is needed. Binary lands at `/opt/homebrew/bin/signal-cli` (Apple Silicon) or `/usr/local/bin/signal-cli` (Intel).

If MacPorts is preferred:

```bash
sudo port install signal-cli
```

## Debian / Ubuntu / Mint

There is no official apt package. Use the upstream tarball plus a Temurin JRE.

```bash
# 1. Java 21
sudo apt-get update
sudo apt-get install -y wget gpg

# Eclipse Adoptium repo
wget -O - https://packages.adoptium.net/artifactory/api/gpg/key/public | sudo gpg --dearmor -o /etc/apt/keyrings/adoptium.gpg
echo "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb $(. /etc/os-release; echo $VERSION_CODENAME) main" | sudo tee /etc/apt/sources.list.d/adoptium.list
sudo apt-get update
sudo apt-get install -y temurin-21-jre

# 2. signal-cli release tarball
SIGNAL_VERSION="0.13.18"   # check https://github.com/AsamK/signal-cli/releases for latest
wget "https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_VERSION}/signal-cli-${SIGNAL_VERSION}.tar.gz"
sudo tar xf "signal-cli-${SIGNAL_VERSION}.tar.gz" -C /opt
sudo ln -sf "/opt/signal-cli-${SIGNAL_VERSION}/bin/signal-cli" /usr/local/bin/signal-cli
```

Bump `SIGNAL_VERSION` to whatever's listed as `Latest` on https://github.com/AsamK/signal-cli/releases.

## RHEL / Fedora / CentOS Stream

Same approach as Debian: install Temurin JDK 21 from `packages.adoptium.net`, then deploy the tarball under `/opt`.

```bash
sudo dnf install -y wget tar
sudo dnf install -y java-21-openjdk   # OR Temurin from adoptium repo
SIGNAL_VERSION="0.13.18"
wget "https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_VERSION}/signal-cli-${SIGNAL_VERSION}.tar.gz"
sudo tar xf "signal-cli-${SIGNAL_VERSION}.tar.gz" -C /opt
sudo ln -sf "/opt/signal-cli-${SIGNAL_VERSION}/bin/signal-cli" /usr/local/bin/signal-cli
```

## Arch Linux

```bash
sudo pacman -S signal-cli
```

The package pulls in `jre-openjdk` automatically.

## Nix / NixOS

Ad hoc shell:

```bash
nix-shell -p signal-cli
```

NixOS module:

```nix
environment.systemPackages = [ pkgs.signal-cli ];
```

## Windows (manual)

1. Install Eclipse Temurin JDK 21 from https://adoptium.net.
2. Download the latest `signal-cli-<version>.zip` from the GitHub releases page.
3. Extract to `C:\Program Files\signal-cli`.
4. Add `C:\Program Files\signal-cli\bin` to PATH (or set `SIGNAL_CLI_BIN` to the full path of `signal-cli.bat`).

WSL is recommended over native Windows when possible — every published recipe targets Linux.

## Docker (containerised)

For ephemeral usage or when host Java conflicts are unwanted:

```bash
docker run --rm -it -v "$HOME/.local/share/signal-cli:/var/lib/signal-cli" \
  registry.gitlab.com/packaging/signal-cli/signal-cli-native:latest --help
```

The MCP server expects `signal-cli` on PATH; wrap docker with a shell script and point `SIGNAL_CLI_BIN` at it if going this route.

## Native (GraalVM) builds

`signal-cli-native` releases use a single-binary GraalVM image with much faster startup (~0.3s vs ~3s on the JVM). Available on the GitHub releases page. Drop-in replacement: rename to `signal-cli` and put on PATH.

## Verification

After any install:

```bash
which signal-cli
signal-cli --version
java --version       # must report 21 or higher (skip if using signal-cli-native)
```

If the MCP plugin still can't find it after a successful CLI invocation, set `SIGNAL_CLI_BIN` to the absolute path returned by `which signal-cli`.
