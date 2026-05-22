#!/usr/bin/env bash
# Pre-flight gate for `make sign` / CI signing. Catches the cheap,
# locally-detectable failures BEFORE the macos-15 runner consumes
# minutes. Run from the repo root.
#
# Checks performed:
#   1. macos/Harlo.app/Contents/Info.plist parses (PlistBuddy/Python).
#   2. macos/Harlo.app/Contents/Entitlements.plist parses.
#   3. CFBundleIdentifier == com.harlo.app (Phase 5A invariant).
#   4. NSAppTransportSecurity exemptions are absent.
#   5. Hardened-runtime entitlement allow-* keys are absent (would
#      weaken signing surface). Phase 5A starts strict per Entitlements.plist.
#   6. All three launchd plists parse and have a non-empty Label.
#   7. Phase 5B: HarloHealthBridge project.yml + entitlements parse,
#      DEVELOPMENT_TEAM matches APPLE_TEAM_ID.
#   8. docs/SIGNING.md documents each required GitHub Secret.
#   9. macos-build.yml references only the documented secrets (no
#      undocumented secret reads that would silently fail in CI).
#
# Exits 0 on full readiness, 1 on any failure. Prints a punch list.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEAM_ID="${APPLE_TEAM_ID:-233JSS4X69}"

FAILURES=0
PASSED=0

red()    { printf "\033[31m%s\033[0m\n" "$1"; }
green()  { printf "\033[32m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

pass() { green "  PASS  $1"; PASSED=$((PASSED+1)); }
fail() { red   "  FAIL  $1"; FAILURES=$((FAILURES+1)); }
note() { yellow "  NOTE  $1"; }

# --------------------------------------------------------------------
# 1. Info.plist parses + bundle id is correct
# --------------------------------------------------------------------
echo "Checking Harlo.app bundle metadata…"

INFO_PLIST="$ROOT/macos/Harlo.app/Contents/Info.plist"
if [ ! -f "$INFO_PLIST" ]; then
  fail "Info.plist missing at $INFO_PLIST"
else
  if python3 -c "import plistlib,sys; plistlib.loads(open(sys.argv[1],'rb').read())" "$INFO_PLIST" 2>/dev/null; then
    pass "Info.plist parses"
  else
    fail "Info.plist does not parse"
  fi

  BUNDLE_ID="$(python3 -c "import plistlib,sys; print(plistlib.loads(open(sys.argv[1],'rb').read()).get('CFBundleIdentifier',''))" "$INFO_PLIST")"
  if [ "$BUNDLE_ID" = "com.harlo.app" ]; then
    pass "CFBundleIdentifier = com.harlo.app"
  else
    fail "CFBundleIdentifier = '$BUNDLE_ID' (expected com.harlo.app)"
  fi

  if python3 -c "import plistlib,sys; d=plistlib.loads(open(sys.argv[1],'rb').read()); sys.exit(0 if 'NSAppTransportSecurity' not in d else 1)" "$INFO_PLIST"; then
    pass "No NSAppTransportSecurity exemptions"
  else
    fail "NSAppTransportSecurity present in Info.plist — review before signing"
  fi
fi

# --------------------------------------------------------------------
# 2. Entitlements.plist parses + no hardened-runtime relaxations
# --------------------------------------------------------------------
ENT_PLIST="$ROOT/macos/Harlo.app/Contents/Entitlements.plist"
if [ ! -f "$ENT_PLIST" ]; then
  fail "Entitlements.plist missing at $ENT_PLIST"
else
  if python3 -c "import plistlib,sys; plistlib.loads(open(sys.argv[1],'rb').read())" "$ENT_PLIST" 2>/dev/null; then
    pass "Entitlements.plist parses"
  else
    fail "Entitlements.plist does not parse"
  fi

  if grep -q "com.apple.security.cs.allow-" "$ENT_PLIST"; then
    note "Hardened-runtime allow-* exception present — confirm it's intentional and documented in docs/SIGNING.md"
  else
    pass "No hardened-runtime allow-* exceptions"
  fi
fi

# --------------------------------------------------------------------
# 3. launchd plists parse + each has a Label
# --------------------------------------------------------------------
echo
echo "Checking launchd plists…"
for plist in com.harlo.daemon.plist com.harlo.agents.plist com.harlo.healthbridge.plist; do
  path="$ROOT/macos/launchd/$plist"
  if [ ! -f "$path" ]; then
    fail "$plist missing"
    continue
  fi
  label="$(python3 -c "import plistlib,sys; print(plistlib.loads(open(sys.argv[1],'rb').read()).get('Label',''))" "$path" 2>/dev/null || echo "")"
  if [ -z "$label" ]; then
    fail "$plist: parse failed or no Label key"
  else
    pass "$plist: Label=$label"
  fi
done

# --------------------------------------------------------------------
# 4. HealthBridge project.yml + entitlements (Phase 5B)
# --------------------------------------------------------------------
echo
echo "Checking HealthBridge (Phase 5B foundation)…"
PROJECT_YML="$ROOT/macos/HarloHealthBridge/project.yml"
HB_ENT="$ROOT/macos/HarloHealthBridge/Sources/HarloHealthBridge/HarloHealthBridge.entitlements"

if [ -f "$PROJECT_YML" ]; then
  if ! python3 -c "import yaml" 2>/dev/null; then
    note "pyyaml not installed in python3 — skipping project.yml parse check"
  elif python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]).read())" "$PROJECT_YML"; then
    pass "project.yml parses"
  else
    fail "project.yml does not parse (see stderr above)"
  fi
  if grep -q "DEVELOPMENT_TEAM" "$PROJECT_YML"; then
    yml_team="$(grep DEVELOPMENT_TEAM "$PROJECT_YML" | head -1 | awk -F: '{gsub(/[ "]/,"",$2); print $2}')"
    if [ "$yml_team" = "$TEAM_ID" ]; then
      pass "project.yml DEVELOPMENT_TEAM = $TEAM_ID"
    else
      fail "project.yml DEVELOPMENT_TEAM = '$yml_team' (expected $TEAM_ID)"
    fi
  else
    fail "project.yml missing DEVELOPMENT_TEAM"
  fi
else
  note "project.yml missing — Phase 5B not bootstrapped"
fi

if [ -f "$HB_ENT" ]; then
  if python3 -c "import plistlib,sys; plistlib.loads(open(sys.argv[1],'rb').read())" "$HB_ENT" 2>/dev/null; then
    pass "HealthBridge entitlements parse"
  else
    fail "HealthBridge entitlements do not parse"
  fi
  if grep -q "com.apple.developer.healthkit" "$HB_ENT"; then
    pass "HealthKit entitlement declared"
  else
    fail "HealthKit entitlement missing from HealthBridge.entitlements"
  fi
fi

# --------------------------------------------------------------------
# 5. docs/SIGNING.md documents each required GitHub Secret
# --------------------------------------------------------------------
echo
echo "Checking docs/SIGNING.md…"
SIGNING_DOC="$ROOT/docs/SIGNING.md"
REQUIRED_SECRETS=(
  APPLE_TEAM_ID
  APPLE_DEVELOPER_CERT_P12
  APPLE_DEVELOPER_CERT_PASSWORD
  APPLE_DEVELOPER_CERT_IDENTITY
  APP_STORE_CONNECT_API_KEY_ID
  APP_STORE_CONNECT_ISSUER_ID
  APP_STORE_CONNECT_PRIVATE_KEY
  APPLE_NOTARY_KEYCHAIN_PASSWORD
)
if [ ! -f "$SIGNING_DOC" ]; then
  fail "docs/SIGNING.md missing"
else
  for secret in "${REQUIRED_SECRETS[@]}"; do
    if grep -q "\`$secret\`" "$SIGNING_DOC" || grep -q "| $secret " "$SIGNING_DOC"; then
      pass "documented: $secret"
    else
      fail "not documented in docs/SIGNING.md: $secret"
    fi
  done
fi

# --------------------------------------------------------------------
# 6. CI workflow references only documented secrets
# --------------------------------------------------------------------
echo
echo "Checking .github/workflows/macos-build.yml…"
CI_YAML="$ROOT/.github/workflows/macos-build.yml"
if [ ! -f "$CI_YAML" ]; then
  fail "macos-build.yml missing"
else
  while read -r secret; do
    if printf '%s\n' "${REQUIRED_SECRETS[@]}" | grep -qx "$secret"; then
      pass "CI references documented secret: $secret"
    else
      fail "CI references undocumented secret: $secret"
    fi
  done < <(grep -oE 'secrets\.[A-Z_0-9]+' "$CI_YAML" | sed 's/^secrets\.//' | sort -u)
fi

# --------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------
echo
echo "------------------------------------------------------------"
echo "  $PASSED checks passed, $FAILURES failures"
echo "------------------------------------------------------------"

if [ "$FAILURES" -gt 0 ]; then
  red "Signing readiness: NOT READY"
  exit 1
fi

green "Signing readiness: READY"
exit 0
