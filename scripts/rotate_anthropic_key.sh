#!/usr/bin/env bash
#
# rotate_anthropic_key.sh — swap in a NEW Anthropic API key, safely, in one shot.
#
# WHAT IT DOES (all local, on this Mac):
#   1. Reads your new key with the screen hidden (never an argument → never in
#      shell history; never printed or logged).
#   2. Validates it against Anthropic BEFORE changing anything (catches typos).
#   3. Sets it for the current login session (launchctl setenv) — immediate.
#   4. Persists it across reboots via a tiny login agent (chmod 600) so you
#      never have to do this again.
#   5. Bounces the Harlo daemon so it picks up the new key.
#
# WHAT IT DOES NOT DO (only you can, from your phone):
#   - Create the new key / delete the OLD leaked key in the Anthropic console.
#
# USAGE:   bash scripts/rotate_anthropic_key.sh
#          (then paste the new key when prompted)
#
set -euo pipefail

LABEL="com.harlo.env"
AGENT="$HOME/Library/LaunchAgents/$LABEL.plist"

say() { printf '\033[1m%s\033[0m\n' "$*"; }
ok()  { printf '  \033[32m✓\033[0m %s\n' "$*"; }
die() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# 1) Read the new key silently --------------------------------------------------
say "Paste your NEW Anthropic API key (input hidden), then press Enter:"
read -rs NEWKEY; echo
[ -n "${NEWKEY:-}" ] || die "No key entered — nothing changed."
case "$NEWKEY" in
  sk-ant-*) : ;;
  *) die "That doesn't look like an Anthropic key (expected sk-ant-...). Nothing changed." ;;
esac

# 2) Validate it works BEFORE touching anything --------------------------------
say "Validating the new key with Anthropic…"
code="$(curl -sS -o /dev/null -w '%{http_code}' https://api.anthropic.com/v1/models \
  -H "x-api-key: $NEWKEY" -H "anthropic-version: 2023-06-01" || echo 000)"
[ "$code" = "200" ] || die "Anthropic rejected the key (HTTP $code). Check it and re-run; nothing changed."
ok "Key is valid (HTTP 200)."

# 3) Set it for the current login session (immediate) --------------------------
launchctl setenv ANTHROPIC_API_KEY "$NEWKEY"
ok "Set for this login session (launchctl setenv)."

# 4) Persist across reboots via a login agent (chmod 600) ----------------------
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$AGENT" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/launchctl</string>
    <string>setenv</string>
    <string>ANTHROPIC_API_KEY</string>
    <string>$NEWKEY</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict></plist>
PLIST
chmod 600 "$AGENT"
launchctl unload "$AGENT" 2>/dev/null || true
launchctl load   "$AGENT" 2>/dev/null || true
ok "Persisted for future logins → $AGENT (chmod 600)."

# 5) Bounce the Harlo daemon so it re-reads the env ----------------------------
launchctl kickstart -k "gui/$(id -u)/com.harlo.daemon" 2>/dev/null \
  || pkill -f 'twind|harlo.*daemon' 2>/dev/null || true
ok "Harlo daemon bounced — it re-activates on next use (Rule 1: socket-activated)."

# 6) Best-effort smoke test (never prints the key) -----------------------------
HARLO=""
for c in "$(command -v harlo 2>/dev/null || true)" "$PWD/.venv312/bin/harlo" "$HOME/Harlo/.venv312/bin/harlo"; do
  [ -n "$c" ] && [ -x "$c" ] && { HARLO="$c"; break; }
done
if [ -n "$HARLO" ]; then
  "$HARLO" status >/dev/null 2>&1 && ok "harlo status OK" || echo "  (harlo status not reachable — fine; the demo's MCP path uses no key)"
fi

unset NEWKEY
say "DONE — the new key is live and persistent."
echo "→ Last step (phone): delete the OLD/leaked key in the Anthropic console so it can't be used."
