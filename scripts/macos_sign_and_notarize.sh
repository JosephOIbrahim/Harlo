#!/usr/bin/env bash
# Sign + notarize + staple Harlo.app (Phase 5A).
#
# Shared by local development and CI. Reads configuration from
# environment variables (CI exports them from secrets; locally,
# source ~/.config/harlo/notary.env first).
#
# Required env vars:
#   APPLE_TEAM_ID                       e.g. 233JSS4X69
#   APPLE_DEVELOPER_CERT_IDENTITY       "Developer ID Application: <Name> (TEAMID)"
#   APP_STORE_CONNECT_API_KEY_ID
#   APP_STORE_CONNECT_ISSUER_ID
#   APP_STORE_CONNECT_PRIVATE_KEY_PATH  path to AuthKey_<KEY_ID>.p8
#
# Usage:
#   scripts/macos_sign_and_notarize.sh dist/Harlo.app

set -euo pipefail

APP_PATH="${1:-dist/Harlo.app}"
ENTITLEMENTS="${ENTITLEMENTS:-macos/Harlo.app/Contents/Entitlements.plist}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script must run on macOS." >&2
    exit 2
fi

if [[ ! -d "$APP_PATH" ]]; then
    echo "App bundle not found: $APP_PATH" >&2
    exit 1
fi

: "${APPLE_TEAM_ID:?must be set}"
: "${APPLE_DEVELOPER_CERT_IDENTITY:?must be set}"
: "${APP_STORE_CONNECT_API_KEY_ID:?must be set}"
: "${APP_STORE_CONNECT_ISSUER_ID:?must be set}"
: "${APP_STORE_CONNECT_PRIVATE_KEY_PATH:?must be set}"

echo "==> Deep-signing nested binaries first"
# Sign every .so / .dylib / nested .app inside the bundle in
# reverse-depth order so py2app's stripped Rust extension regains
# a valid signature before the outer bundle signature seals it.
find "$APP_PATH" \
    -type f \
    \( -name "*.dylib" -o -name "*.so" \) \
    -print0 |
while IFS= read -r -d '' bin; do
    codesign \
        --force \
        --options=runtime \
        --timestamp \
        --sign "$APPLE_DEVELOPER_CERT_IDENTITY" \
        "$bin"
done

echo "==> Signing the outer app bundle"
if [[ -f "$ENTITLEMENTS" ]]; then
    codesign \
        --force \
        --options=runtime \
        --timestamp \
        --entitlements "$ENTITLEMENTS" \
        --sign "$APPLE_DEVELOPER_CERT_IDENTITY" \
        "$APP_PATH"
else
    codesign \
        --force \
        --options=runtime \
        --timestamp \
        --sign "$APPLE_DEVELOPER_CERT_IDENTITY" \
        "$APP_PATH"
fi

echo "==> Verifying signature locally"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
spctl -a -t exec -vv "$APP_PATH" || echo "(spctl pre-notarize check expected to fail; will re-check post-staple)"

echo "==> Packaging for notarization"
ZIP_PATH="${APP_PATH%.*}.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

echo "==> Submitting to Apple notary service"
xcrun notarytool submit "$ZIP_PATH" \
    --team-id "$APPLE_TEAM_ID" \
    --key "$APP_STORE_CONNECT_PRIVATE_KEY_PATH" \
    --key-id "$APP_STORE_CONNECT_API_KEY_ID" \
    --issuer "$APP_STORE_CONNECT_ISSUER_ID" \
    --wait

echo "==> Stapling the notarization ticket"
xcrun stapler staple "$APP_PATH"

echo "==> Final verification"
codesign -dvvv "$APP_PATH"
spctl -a -t exec -vv "$APP_PATH"

echo "==> Done: $APP_PATH is signed, notarized, and stapled."
