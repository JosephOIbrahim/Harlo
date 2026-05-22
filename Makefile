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
PYTHON ?= python3

.PHONY: help build-rust build-macos sign notarize staple dmg release \
        clean-macos test compliance-greps verify doctor signing-readiness

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
