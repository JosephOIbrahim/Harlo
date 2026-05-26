#!/usr/bin/env bash
# Build a distributable DMG containing a signed/notarized/stapled
# Harlo.app and a friendly README.
#
# Phase 5A: ships Harlo.app only. Phase 5B will add HarloHealthBridge.app
# alongside.
#
# Usage:
#   scripts/macos_build_dmg.sh [output.dmg]

set -euo pipefail

OUTPUT="${1:-dist/Harlo.dmg}"
APP_PATH="${APP_PATH:-dist/Harlo.app}"
STAGING="$(mktemp -d)"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script must run on macOS." >&2
    exit 2
fi

if [[ ! -d "$APP_PATH" ]]; then
    echo "App bundle not found: $APP_PATH" >&2
    echo "Run `make build-macos sign notarize` first." >&2
    exit 1
fi

if ! command -v create-dmg >/dev/null 2>&1; then
    echo "create-dmg not installed. Run: brew install create-dmg" >&2
    exit 1
fi

echo "==> Staging DMG layout in $STAGING"
cp -R "$APP_PATH" "$STAGING/"
cat > "$STAGING/Read Me First.txt" <<'EOF'
Welcome to Harlo.

To install:
  1. Drag Harlo.app into Applications (the alias next to this file).
  2. Open Harlo from /Applications.
  3. On first launch, Harlo will offer to install two background
     services (com.harlo.daemon and com.harlo.agents). Both are
     socket-activated and idle at 0 watts; either can be removed
     later from Harlo settings or with:
         python scripts/macos_install_daemon.py uninstall --all

Everything Harlo remembers about you lives in:
  ~/Library/Application Support/Harlo

No cloud sync, no telemetry. Reading is welcome:
  ~/Library/Application Support/Harlo/twin.db    (SQLite)
EOF

echo "==> Building DMG"
mkdir -p "$(dirname "$OUTPUT")"
rm -f "$OUTPUT"   # create-dmg refuses to overwrite; allow clean re-runs
create-dmg \
    --volname "Harlo" \
    --window-pos 200 120 \
    --window-size 600 360 \
    --icon-size 96 \
    --icon "Harlo.app" 160 180 \
    --hide-extension "Harlo.app" \
    --app-drop-link 440 180 \
    --no-internet-enable \
    "$OUTPUT" \
    "$STAGING"

rm -rf "$STAGING"

echo "==> DMG ready: $OUTPUT"
ls -lh "$OUTPUT"

# Sign + notarize + staple the DMG wrapper so the disk image opens with no
# Gatekeeper warning on download. The app inside is already notarized; this
# covers the container. Sources the same notary.env the Makefile `sign`
# target uses; skips gracefully when signing config is absent (CI dry runs).
if [[ -f "$HOME/.config/harlo/notary.env" ]]; then
    set -a; . "$HOME/.config/harlo/notary.env"; set +a
fi
if [[ -n "${APPLE_DEVELOPER_CERT_IDENTITY:-}" && -n "${APPLE_TEAM_ID:-}" \
   && -n "${APP_STORE_CONNECT_API_KEY_ID:-}" && -n "${APP_STORE_CONNECT_ISSUER_ID:-}" \
   && -n "${APP_STORE_CONNECT_PRIVATE_KEY_PATH:-}" ]]; then
    echo "==> Signing the DMG"
    codesign --force --timestamp --sign "$APPLE_DEVELOPER_CERT_IDENTITY" "$OUTPUT"
    echo "==> Notarizing the DMG (Apple notary service; minutes)"
    xcrun notarytool submit "$OUTPUT" \
        --team-id "$APPLE_TEAM_ID" \
        --key "$APP_STORE_CONNECT_PRIVATE_KEY_PATH" \
        --key-id "$APP_STORE_CONNECT_API_KEY_ID" \
        --issuer "$APP_STORE_CONNECT_ISSUER_ID" \
        --wait
    echo "==> Stapling the DMG"
    xcrun stapler staple "$OUTPUT"
    echo "==> Verifying the notarized DMG"
    spctl --assess --type install --verbose "$OUTPUT" || true
else
    echo "==> Skipping DMG sign/notarize (signing config not present)"
fi
