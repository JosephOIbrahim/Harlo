# Signing & Notarization Runbook

Apple Team ID: **`233JSS4X69`** (Individual enrollment, Apple
Developer Program).

This document is the operator-side checklist for getting Harlo
signed, notarized, and distributable. It pairs with:

- `Makefile` (`build-macos`, `sign`, `notarize`, `dmg`)
- `scripts/macos_sign_and_notarize.sh` (local + CI shared script)
- `scripts/macos_build_dmg.sh`
- `setup_py2app.py`
- `.github/workflows/macos-build.yml`

## Phase 5A scope: `Harlo.app` only

This phase signs and notarizes the Python-bundled `Harlo.app`.
`HarloHealthBridge.app` is intentionally held back to Phase 5B so
that any HealthKit entitlement surprise is isolated from the basic
signing pipeline.

## One-time Apple Developer portal setup (~30 minutes)

Performed by the human operator at <https://developer.apple.com/account>.

### 1. Generate a Developer ID Application certificate

1. Developer portal → **Certificates, Identifiers & Profiles**.
2. **Certificates** → "+" → **Developer ID Application**.
3. Follow the CSR flow (Keychain Access → Certificate Assistant →
   Request from a Certificate Authority).
4. Download the issued `.cer`, double-click to install into the
   local Keychain.
5. In Keychain Access, locate the certificate, right-click →
   **Export** → save as `.p12` with a strong password.

### 2. Register the bundle ID

1. Developer portal → **Identifiers** → "+" → **App IDs** → **App**.
2. Description: `Harlo`. Bundle ID: `com.harlo.app` (Explicit).
3. Capabilities: none required for Phase 5A.
4. Register.

(Phase 5B adds `com.harlo.healthbridge` + the HealthKit capability.)

### 3. Create an App Store Connect API key for `notarytool`

`notarytool` is Apple's current notarization CLI (since November
2023; `altool` is deprecated).

1. <https://appstoreconnect.apple.com> → **Users and Access** →
   **Integrations** → **App Store Connect API**.
2. "+" → name `harlo-notary`, access **Developer**.
3. Download the `.p8` file (you can only do this once — save it).
4. Note the **Key ID** and **Issuer ID** displayed on the page.

### 4. Add GitHub Secrets

In the GitHub repo settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `APPLE_TEAM_ID` | `233JSS4X69` |
| `APPLE_DEVELOPER_CERT_P12` | `base64 -i developer_id.p12 \| pbcopy` then paste |
| `APPLE_DEVELOPER_CERT_PASSWORD` | the password you used during .p12 export |
| `APPLE_DEVELOPER_CERT_IDENTITY` | `Developer ID Application: <Your Name> (233JSS4X69)` exactly as it appears in Keychain Access |
| `APP_STORE_CONNECT_API_KEY_ID` | the Key ID from step 3 |
| `APP_STORE_CONNECT_ISSUER_ID` | the Issuer ID from step 3 |
| `APP_STORE_CONNECT_PRIVATE_KEY` | `cat AuthKey_<KEY_ID>.p8` — paste full file contents |
| `APPLE_NOTARY_KEYCHAIN_PASSWORD` | any random string (used inside CI's ephemeral keychain) |

## Local build environment

The signing chain (`build-macos`, `sign`, `notarize`, `dmg`) is
validated end-to-end on CI's macos-15 runner with **Python 3.12**.
Local builds need the same runtime: py2app's `modulegraph` 0.19.7
hits an AST-recursion bug on Python 3.14 that does not affect 3.12.

If your project venv (`.venv314/`) is on 3.14 — which is what the
rest of Harlo development uses — keep a separate 3.12 venv for
bundling:

```sh
python3.12 -m venv .venv-bundle
.venv-bundle/bin/pip install maturin py2app click jsonschema numpy mcp pyyaml pydantic
PYTHON=.venv-bundle/bin/python make build-macos
```

For tests + verify (`make verify`), 3.14 is fine — the Makefile
auto-detects `.venv314/` when no `PYTHON=` is passed.

## Local dry run before pushing to CI

A first local pass catches problems faster than CI's macos-15 runner.

```sh
# 1. Build the Rust hot path
make build-rust

# 2. Build the Python bundle
make build-macos

# 3. Sign + notarize (reads ~/.config/harlo/notary.env)
make sign notarize

# 4. Package
make dmg

# 5. Verify
spctl -a -t exec -vv dist/Harlo.app          # → "accepted source=Notarized Developer ID"
codesign -dvvv dist/Harlo.app                # → identifier=com.harlo.app, runtime, Team ID=233JSS4X69
```

`~/.config/harlo/notary.env` for local runs:

```sh
APPLE_TEAM_ID=233JSS4X69
APPLE_DEVELOPER_CERT_IDENTITY="Developer ID Application: <Your Name> (233JSS4X69)"
APP_STORE_CONNECT_API_KEY_ID=<key id>
APP_STORE_CONNECT_ISSUER_ID=<issuer id>
APP_STORE_CONNECT_PRIVATE_KEY_PATH=/path/to/AuthKey_<KEY_ID>.p8
```

## CI trigger

Push a tag matching `v*.*.*`:

```sh
git tag v0.1.0
git push origin v0.1.0
```

This runs `.github/workflows/macos-build.yml`, produces a notarized,
stapled DMG, and attaches it to a draft GitHub Release.

## Hardened runtime entitlements

`Harlo.app` is signed with `--options=runtime`. The default hardened
runtime is strict — if Python or a C extension trips it at signing
or runtime, you'll see a Gatekeeper rejection. Possible fallback
entitlements (add to `macos/Harlo.app/Contents/Entitlements.plist`
ONLY when a specific runtime failure forces it, and document the
failing log here):

| Entitlement | When |
|---|---|
| `com.apple.security.cs.allow-unsigned-executable-memory` | A C extension triggers `EXC_BAD_ACCESS (KERN_PROTECTION_FAILURE)`. |
| `com.apple.security.cs.disable-library-validation` | A dlopen target fails to load with `errSecCSReqFailed`. |

Resist adding these speculatively — every one weakens the hardened
runtime contract.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `notarytool` says "Invalid" with no detail | Stapler ticket not yet generated | Wait 1–2 min; rerun `notarytool log <id>` |
| `codesign` fails on a `.so` inside the bundle | Rust `.dylib` lost signature when py2app stripped | Sign the `.dylib` separately before deep-signing the `.app` |
| Gatekeeper rejects with "developer cannot be verified" | Notarization succeeded but stapler skipped | `xcrun stapler staple dist/Harlo.app` |
| `spctl -a` says "not accepted" | Hardened runtime entitlement missing | See table above |
| HealthKit consent dialog never appears (Phase 5B) | `com.harlo.healthbridge` not registered in portal, or capability not enabled | Re-check developer portal Identifiers page |

## Phase 5B preview (not yet active)

Once Phase 5A produces a green DMG, Phase 5B will:

1. Register `com.harlo.healthbridge` in the portal.
2. Enable the **HealthKit** capability on that identifier (one
   click; no separate Apple approval needed for Developer ID Mac
   apps per our 2025/2026 research).
3. Land `macos/HarloHealthBridge/project.yml` (xcodegen spec).
4. Extend the CI workflow with a second job that builds + signs +
   notarizes the bridge and bundles it into the same DMG.
