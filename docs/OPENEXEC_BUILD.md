# OpenExec Build Report — Sprint 2 Phase 0

## Date: 2026-03-30

## Platform
- **OS:** Windows 11 Pro for Workstations 10.0.26200
- **CPU:** AMD Threadripper PRO 7965WX
- **GPU:** RTX 4090
- **RAM:** 128GB DDR5
- **Compiler:** MSVC 19.44.35222 (VS2022 Build Tools)
- **CMake:** 4.2.1
- **Python:** 3.12.10 (for USD build), 3.14.2 (project venv)

## Build Status

### USD 26.03 Core: SUCCESS
- **Build command:** `build_usd.py --no-imaging --no-usdview --no-ptex --no-embree --no-tests --no-examples --no-tutorials --no-docs --build-args USD,"-DPXR_BUILD_EXEC=ON" C:\USD\26.03-exec`
- **Install path:** `C:\USD\26.03-exec`
- **Build time:** ~10 minutes
- **Python import:** `from pxr import Usd` works, reports version `(0, 26, 3)`

### OpenExec C++ Libraries: BUILT
```
usd_exec.dll       ✓
usd_execGeom.dll   ✓
usd_execIr.dll     ✓
usd_execUsd.dll    ✓
```
C++ headers installed at `include/pxr/exec/`.
Plugins registered: `exec`, `execGeom`, `execIr`, `execUsd`.

### OpenExec Python Bindings: NOT AVAILABLE
**Zero Python bindings exist in the USD 26.03 source tree.**
- No `wrap*.cpp` files in any `pxr/exec/*/` subdirectory
- No `module*.cpp` files
- No `python/` subdirectories
- `from pxr import Exec` fails with `ImportError`

This means OpenExec is **C++ only** in the initial v26.03 release.

### usdGenSchema: AVAILABLE
- Binary at `C:\USD\26.03-exec\bin\usdGenSchema`
- Requires Jinja2 (installed)

## Circuit Breaker: TRIGGERED

Per AGENTS.md Circuit Breaker protocol:

> "OpenExec is 4 days old in the wild (USD v26.03 shipped March 26, 2026).
> Non-Pixar developers building it from source is uncharted territory."

> "Do not treat a build failure as a project failure. Harlo works
> today on MockCogExec. OpenExec is the upgrade, not the requirement."

### What Works
1. USD 26.03 builds and imports in Python ✓
2. OpenExec C++ libraries compile ✓
3. Exec C++ plugins register in Plug.Registry ✓
4. usdGenSchema available ✓

### What's Blocked
1. No Python bindings for OpenExec — cannot call from Python
2. Phases 1-5 of Sprint 2 require Python Exec API access

### Fallback
Sprint 1 MockCogExec continues to serve. The architecture is OpenExec-native.
The implementation catches up when Pixar ships Python bindings for OpenExec.

### Attempts
1. **pip usd-core 26.3** — no Exec module included
2. **Source build without --build-args** — Exec libraries not built (PXR_BUILD_EXEC defaulted ON but Python bindings missing from source)
3. **Source build with -DPXR_BUILD_EXEC=ON** — C++ libraries built, but no Python wrapping exists in v26.03 source
