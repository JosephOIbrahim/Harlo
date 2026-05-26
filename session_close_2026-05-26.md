# Session Close — 2026-05-26

**The day Harlo shipped its first notarized macOS release (v0.1.0).**

Release: https://github.com/JosephOIbrahim/Harlo/releases/tag/v0.1.0

---

## What shipped

- **v0.1.0 — first notarized macOS release.** Tag `v0.1.0` @ `6bf82e0`,
  Cognitive Twin **v6.1-MOTOR**.
  - Signed + notarized + stapled **Harlo.app (89 MB)** and **Harlo.dmg (32 MB)**
    — Developer ID Application (Team `233JSS4X69`), hardened runtime, bundle id
    `com.josephibrahim.harlo`. Both `spctl`-accepted, ticket stapled.
  - **Lexical Rust encoder** runtime (the intended v0.1.0 ship state); the
    semantic/ML stack is excluded from the bundle.
- **RSI notification** — `harness/path_d/rsi_notification_2026-05-26.md` authored
  + committed on `harness-path-d` (`ab451d5`), **staged for architect delivery**
  (not sent to RSI).
- **PR #11 disposition** — left **OPEN / deferred**. Path D v1 stays on its
  branch; merging would shift `make verify` 1,365 → 1,387 and isn't on the
  v0.1.0 critical path. Merges cleanly post-release.

## Release-build arc (the path wasn't clean — every snag diagnosed + fixed)

- **D48** filed (`RELEASE_DECISIONS.md`): pragmatic-key decision + no-credentials-
  in-chat forward rule + post-release key-rotation TODO.
- **Bundle ID** renamed `com.harlo.app` → `com.josephibrahim.harlo` (original was
  globally taken).
- **Apple signing brought up:** Developer ID cert imported into login keychain;
  `find-identity` showed 0 valid until the **Developer ID G2/G1 intermediate
  CAs** were installed (chain completion — Branch B fix). `notary.env` written
  (`~/.config/harlo/`, chmod 600); notarytool auth confirmed.
- **`.venv312`** built for py2app — Python 3.14 trips py2app's modulegraph
  recursion, so 3.12 is the build interpreter (`brew install python@3.12
  create-dmg`).
- **Two notarization rejections** diagnosed via Apple's notary log, both fixed:
  1. protobuf's C-extension trapped inside `python312.zip` (unsignable) →
     excluded the ML stack (`setup_py2app.py`), 441 MB → 89 MB.
  2. `Python.framework` binary + `MacOS/python` left unsigned →
     `macos_sign_and_notarize.sh` now signs **all** nested Mach-O by content.
- **DMG** itself signed + notarized + stapled (reproducible step added to
  `macos_build_dmg.sh`) — no Gatekeeper warning on download.
- **CI** (`macos-build.yml`): graceful-skip added — tag-push build skips
  sign/notarize/release cleanly when the 8 signing secrets are absent (green
  build-only canary); full pipeline activates once secrets are set.

## Carry-forward

- **TI-002** — test suite non-hermetic with the analytic corpus (Harlo-wide;
  LABRE downstream inherits it).
- **TI-003** — reference predictor has target leakage + undefined horizon;
  cognitive-state forecasting not yet evidence-grade. **Highest-leverage next
  surgery.**
- **RSI items 3–7** — GEPA ownership, shadow-rollout location, CMP, LABRE
  intra-session routing, Honcho dialectic observability. Block any PVH v2.
- **PR #11 (Path D v1)** — merge post-release: add `joblib` to `lint.yml`'s CI
  deps (or `importorskip`), accept the deliberate 1,365 → 1,387 baseline bump.
- **CI signing track** — 8 GitHub secrets deferred (`docs/APPLE_SECRETS_SETUP.md`);
  set them if CI-side signing is wanted (local DMG is the release artifact).
- **Semantic encoder build** — a `[semantic]` bundle variant if the ML encoder
  path ships.
- **Post-release credential rotation** (D48) — revoke + regenerate the App Store
  Connect API key, re-export the `.p12` with a new password.
- **RSI notification delivery** — staged on `harness-path-d`; architect to send.

## Pointer files

- Release: https://github.com/JosephOIbrahim/Harlo/releases/tag/v0.1.0 · tag
  `v0.1.0` @ `6bf82e0`
- Decisions: `RELEASE_DECISIONS.md` (D48)
- Signing: `docs/SIGNING.md`, `docs/APPLE_SECRETS_SETUP.md`,
  `scripts/macos_sign_and_notarize.sh`, `scripts/macos_build_dmg.sh`,
  `~/.config/harlo/notary.env` (local, 600)
- Path D (PR #11 / `harness-path-d`): `session_close_2026-05-25.md`,
  `tracking_issues.md` (TI-002/003), `05_DECISIONS.md` (D20–D47),
  `rsi_notification_2026-05-26.md`
- Build env: `.venv312` (py2app), `python@3.12` + `create-dmg` (brew)

## State at close

- `master` @ `6bf82e0`, pushed. Tag `v0.1.0` pushed; GitHub release **published**
  with `Harlo.dmg`.
- Tag-push CI: graceful-skip canary (in progress at close; expected green).
- Working tree clean.

---

**End of session. Harlo v0.1.0 is live and notarized.**
