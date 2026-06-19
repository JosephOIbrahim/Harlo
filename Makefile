# Harlo top-level Makefile.
#
# Targets prefixed with `build-` produce artifacts; `sign`, `notarize`,
# `staple`, `dmg` operate on those artifacts. `release` chains the
# whole pipeline.
#
# macOS-only targets (`build-macos`, `sign`, `notarize`, `dmg`,
# `release`) abort with a friendly message when run on other platforms.

UNAME_S := $(shell uname -s)
APP_PATH ?= dist/Harlo.app
DMG_PATH ?= dist/Harlo.dmg

# HarloHealthBridge (Phase 5B) build knobs. Local-dev defaults; CI / release
# overrides HB_CODESIGN_ID with the "Developer ID Application" identity.
APPLE_TEAM_ID  ?= 233JSS4X69
HB_CONFIG      ?= Release
HB_CODESIGN_ID ?= Apple Development

# Python resolution order:
#   1. Explicit override on the command line (PYTHON=...)
#   2. Currently-activated venv ($VIRTUAL_ENV)
#   3. Project venv at .venv314/bin/python (the convention used in
#      the dev runbook — see CLAUDE.md "single venv" note)
#   4. System python3
# Lets `make verify` work without manual override on a fresh shell
# in the project root.
ifndef PYTHON
  ifdef VIRTUAL_ENV
    PYTHON := $(VIRTUAL_ENV)/bin/python
  else ifneq (,$(wildcard .venv314/bin/python))
    PYTHON := .venv314/bin/python
  else
    PYTHON := python3
  endif
endif

.PHONY: help build-rust build-macos sign notarize staple dmg release \
        clean-macos test compliance-greps verify doctor signing-readiness \
        regen-trajectories regen-predictor build-healthbridge

help:
	@echo "Harlo build targets"
	@echo "  build-rust       Build the Rust hot path (maturin develop --release)"
	@echo "  build-macos      Build dist/Harlo.app via py2app (macOS only)"
	@echo "  sign             codesign Harlo.app with the Developer ID (macOS only)"
	@echo "  notarize         Submit to Apple's notary service (macOS only)"
	@echo "  staple           Staple the notarization ticket (rolled into sign for now)"
	@echo "  dmg              Build dist/Harlo.dmg (macOS only)"
	@echo "  release          build-macos -> sign -> notarize -> dmg"
	@echo "  test             Run cargo + pytest"
	@echo "  compliance-greps Run all CLAUDE.md compliance greps"
	@echo "  doctor           Run harlo doctor --strict (operator readiness)"
	@echo "  signing-readiness Run pre-flight gate before signing"
	@echo "  verify           test + compliance-greps + doctor + signing-readiness"
	@echo "  regen-trajectories  Regenerate data/trajectories_10k.jsonl (~229 MB, ~minutes)"
	@echo "  regen-predictor     regen-trajectories + train models/cognitive_predictor_v1.joblib"
	@echo "  clean-macos      Remove dist/ and build/"

build-rust:
	maturin develop --release

build-macos:
ifeq ($(UNAME_S),Darwin)
	rm -rf build dist
	$(PYTHON) setup_py2app.py py2app
	@echo "==> Built $(APP_PATH)"
else
	@echo "build-macos: skipped on $(UNAME_S) (macOS only)"
endif

# Phase 5B: build HarloHealthBridge.app with the bundled HarloXPCRelay
# (xcodegen tool target → Contents/Helpers/, app signature seals it). Notarization
# is handled separately by the sign chain. Run AFTER build-macos (which wipes build/).
build-healthbridge:
ifeq ($(UNAME_S),Darwin)
	command -v xcodegen >/dev/null 2>&1 || brew install xcodegen
	xcodegen generate --spec macos/HarloHealthBridge/project.yml
	xcodebuild -project macos/HarloHealthBridge/HarloHealthBridge.xcodeproj \
	    -scheme HarloHealthBridge -configuration $(HB_CONFIG) \
	    -allowProvisioningUpdates CODE_SIGN_STYLE=Automatic \
	    DEVELOPMENT_TEAM=$(APPLE_TEAM_ID) CODE_SIGN_IDENTITY="$(HB_CODESIGN_ID)" \
	    ENABLE_DEBUG_DYLIB=NO ENABLE_PREVIEWS=NO MACOSX_DEPLOYMENT_TARGET=13.0 \
	    -derivedDataPath build/hb build
	@echo "==> Built HarloHealthBridge.app + embedded HarloXPCRelay (build/hb/Build/Products/$(HB_CONFIG)/)"
else
	@echo "build-healthbridge: skipped on $(UNAME_S) (macOS only)"
endif

sign:
ifeq ($(UNAME_S),Darwin)
	@if [ -f $(HOME)/.config/harlo/notary.env ]; then \
	    set -a; . $(HOME)/.config/harlo/notary.env; set +a; \
	fi; \
	bash scripts/macos_sign_and_notarize.sh $(APP_PATH)
else
	@echo "sign: skipped on $(UNAME_S) (macOS only)"
endif

# Kept as separate targets for clarity; the shared script does
# sign+notarize+staple in one pass.
notarize: sign
staple: sign

dmg:
ifeq ($(UNAME_S),Darwin)
	bash scripts/macos_build_dmg.sh $(DMG_PATH)
else
	@echo "dmg: skipped on $(UNAME_S) (macOS only)"
endif

release: build-macos sign dmg
	@echo "==> Release artifacts:"
	@ls -lh dist/

clean-macos:
	rm -rf dist build

test:
	cargo test -p hippocampus
	$(PYTHON) -m pytest tests/ -v

compliance-greps:
	@# --include='*.py' / -F '*.py' filters skip __pycache__ bytecode,
	@# which legitimately contains the forbidden tokens as string
	@# constants inside the doctor module (itself a compliance checker).
	@echo "=== sleep( ==="; \
	    ! grep -rn --include='*.py' "sleep(" python/harlo/ || (echo "FAIL: sleep() found" && exit 1)
	@echo "=== while True ==="; \
	    ! grep -rn --include='*.py' "while True" python/harlo/ || (echo "FAIL: while True found" && exit 1)
	@# Filter legitimate hits: Rust doc-comments (// /// //!) and
	@# `fn test_*` function names. Mirrors the comment filter used by
	@# tests/test_integration/test_compliance.py so the bash and pytest
	@# layers agree.
	@echo "=== float32 in crates ==="; \
	    ! grep -rnE "float32" crates/ | grep -vE ':[0-9]+:[[:space:]]*(//|fn[[:space:]]+test_)' || \
	    (echo "FAIL: float32 found" && exit 1)
	@echo "=== cosine in crates ==="; \
	    ! grep -rnE "cosine" crates/ | grep -vE ':[0-9]+:[[:space:]]*(//|fn[[:space:]]+test_)' || \
	    (echo "FAIL: cosine found" && exit 1)
	@echo "=== biometric in elenchus/bridge ==="; \
	    ! grep -rn --include='*.py' "biometric" python/harlo/elenchus/ python/harlo/bridge/ 2>/dev/null || \
	    (echo "FAIL: biometric leaked" && exit 1)
	@echo "all compliance greps passed"

doctor:
	PYTHONPATH=python $(PYTHON) -m harlo.cli.main doctor --strict

signing-readiness:
	bash scripts/check_signing_readiness.sh

verify: test compliance-greps doctor signing-readiness

# Synthetic training data for the cognitive predictor. Profile-driven Markov
# sim from src/trajectory_generator.py — 10K sessions seeded for repro.
# Gitignored due to size (~229 MB); regenerate locally as needed.
data/trajectories_10k.jsonl regen-trajectories:
	$(PYTHON) -m src.trajectory_generator \
	    --count 10000 --seed 42 --validate \
	    --output data/trajectories_10k.jsonl

# XGBoost MultiOutputRegressor trained on the trajectories. Gitignored
# (385 KB binary that's reproducible from --seed 42 + the data above).
# Five tests in test_sprint*/test_recalibration/test_schedule depend on
# this artifact — they `pytest.skip` cleanly when it's missing, so the
# regen is opt-in.
models/cognitive_predictor_v1.joblib regen-predictor: data/trajectories_10k.jsonl
	$(PYTHON) -m src.train_predictor \
	    --data data/trajectories_10k.jsonl \
	    --output models/cognitive_predictor_v1.joblib \
	    --seed 42
