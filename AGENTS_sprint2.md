# AGENTS.md — Cognitive Twin Sprint 2
# Native OpenExec: Replace MockCogExec with C++ Computation Plugins
# Author: Joseph O. Ibrahim
# Date: March 30, 2026
# Prerequisite: Sprint 1 complete (84 tests passing, MockCogExec functional)

---

## CONSTITUTION (Unchanged from Sprint 1 — Still Law)

### LAW 1: SCOUT BEFORE YOU ACT
### LAW 2: VERIFY AFTER EVERY MUTATION
### LAW 3: BOUNDED FAILURE → ESCALATE (3 retries then stop)
### LAW 4: COMPLETE OUTPUT OR EXPLICIT BLOCKER
### LAW 5: ROLE ISOLATION
### LAW 6: EXPLICIT HANDOFFS
### LAW 7: ADVERSARIAL VERIFICATION
### LAW 8: HUMAN GATES AT IRREVERSIBLE TRANSITIONS

Full text in Sprint 1 AGENTS.md (AGENTS_sprint1.md). All eight laws apply unchanged.

---

## MISSION

Replace the Sprint 1 Python mock (MockCogExec + networkx DAG) with native USD 26 OpenExec computation plugins. The cognitive state machines become C++ callbacks compiled into a plugin library, evaluated by OpenExec's multithreaded engine against a real USD stage.

**The contract:** Sprint 1's 84 tests are the verification suite. Every test that passed against MockCogExec must produce identical results against native OpenExec. Same inputs → same outputs. When that's true, MockCogExec is deleted.

**The risk:** The USD 26 build environment. If it won't compile, nothing else in this sprint matters. Phase 0 exists to kill this risk immediately.

---

## COMMANDMENTS (Sprint 2 Specific)

1. **Sprint 1 tests are sacred.** The 84 Sprint 1 tests AND the 890 existing tests are invariants. Breaking any is higher priority than any Sprint 2 work.
2. **USDA schemas first, C++ second.** Define schemas in USDA. Generate boilerplate via `usdGenSchema`. Write computation callbacks in the generated structure. Do not hand-write USD schema boilerplate.
3. **Parameterized, not hardcoded.** C++ callbacks read thresholds from USD stage attributes. `building_task_threshold`, `rolling_coherence_threshold`, etc. are USD attributes, not C++ constants. Personality tuning via USDA, not recompilation.
4. **Anchor immunity is structural.** AnchorPhaseAPI and ModulatedPhaseAPI are separate schemas with separate registered callbacks. There is no code path from injection parameters to anchor gain output.
5. **Time-sampled state.** Computations read `exchange_index` t-1 from authored time samples. No self-referential queries. No cycles. OpenExec cycle detector will abort if violated.
6. **Headless build.** `build_usd.py --no-imaging --no-usdview --no-ptex --no-embree --openexec`. Strip all VFX rendering. USD is a data substrate here, not a graphics engine.
7. **MockCogExec is the oracle.** When in doubt about what a computation should return, run the Sprint 1 Python mock. The C++ callback must produce the same result.
8. **If the build fails after 3 attempts, STOP.** Surface the exact error, the platform, the CMake output. Do not attempt heroic workarounds. This is a known high-risk phase.

---

## PLATFORM DETECTION

Sprint 2 must determine which machine to build on:

| Machine | OS | CPU | GPU | USD Build Feasibility |
|---------|-----|-----|-----|----------------------|
| Threadripper Workstation | Windows 11 Pro | AMD 7965WX | RTX 4090 | Possible but harder. MSVC + CMake. |
| Mac Studio | macOS | Apple M1 | Integrated | Recommended by Gemini. Clang + CMake. ~15min headless. |

Phase 0 determines which platform succeeds first.

---

## PHASE 0: USD 26 BUILD ENVIRONMENT (The Gate-of-Gates)

### Purpose
This is the single highest-risk task in Sprint 2. If USD 26 + OpenExec won't compile on your hardware, everything downstream is blocked. Kill this risk first.

### Tasks:

1. **Check if USD is already available:**
   ```bash
   python -c "from pxr import Usd; print(Usd.GetVersion())"
   ```
   If this works and reports 26.x, skip to Task 5.

2. **Check prerequisites:**
   ```bash
   cmake --version          # Need 3.24+
   python --version         # Need 3.10-3.12 (USD constraint)
   git --version
   ```
   On Windows: verify MSVC/Visual Studio build tools installed.
   On macOS: verify Xcode command-line tools (`xcode-select --install`).

3. **Clone OpenUSD:**
   ```bash
   git clone https://github.com/PixarAnimationStudios/OpenUSD.git
   cd OpenUSD
   git checkout v26.03    # or latest 26.x tag
   ```

4. **Headless build with OpenExec (Gemini R2 recommended flags):**
   ```bash
   python build_scripts/build_usd.py \
       --no-imaging \
       --no-usdview \
       --no-ptex \
       --no-embree \
       --openexec \
       /opt/usd-26.03
   ```
   On Windows, adjust install path: `C:\USD\26.03`

   **Expected:** ~15 minutes on Mac Studio. ~20-30 minutes on Threadripper.
   **If it fails:** Capture full CMake output + error. Surface as blocker. Do NOT retry with different flags without human approval.

5. **Verify OpenExec is functional:**
   ```python
   from pxr import Usd, Exec
   stage = Usd.Stage.CreateInMemory()
   print("USD version:", Usd.GetVersion())
   print("OpenExec available:", hasattr(Exec, 'ExecUsdSystem'))
   ```

6. **Verify usdGenSchema works:**
   ```bash
   usdGenSchema --help
   ```
   Must be on PATH from the USD install.

### Verification:
- USD 26 imports in Python
- OpenExec module accessible
- usdGenSchema executable
- No existing tests broken

### Gate: Print USD version, OpenExec status, platform info. Stop if build fails.
### Git: `git commit -m "Sprint 2 Phase 0: USD 26 + OpenExec build verified"`

### CIRCUIT BREAKER:
If the build fails after 3 attempts on the primary platform:
1. Try the secondary platform (if Threadripper fails, try Mac Studio or vice versa)
2. If both fail: surface blocker. Sprint 2 pauses. Sprint 1 MockCogExec continues to serve. This is acceptable — the architecture is OpenExec-native, the implementation catches up later.

---

## PHASE 1: USDA Schema Definitions + usdGenSchema

### Gate: Phase 0 passed (USD 26 builds, OpenExec available).

### Tasks:

1. **Create USDA schema files** under `schemas/`:

   **`schemas/cognitiveStatePrim.usda`:**
   ```usda
   #usda 1.0
   (
       subLayers = [
           @usd/schema.usda@
       ]
   )

   class "CognitiveStatePrimAPI"
   (
       inherits = </APISchemaBase>
       customData = {
           token apiSchemaType = "singleApply"
           dictionary schemaTokens = {
               dictionary computeMomentum = {}
               dictionary computeBurnout = {}
               dictionary computeEnergy = {}
               dictionary computeBurst = {}
               dictionary computeAllostatic = {}
               dictionary computeRouting = {}
               dictionary computePermission = {}
           }
       }
   )
   {
       int momentum = 1                                (doc = "0=crashed,1=cold_start,2=building,3=rolling,4=peak")
       int burnout = 0                                 (doc = "0=GREEN,1=YELLOW,2=ORANGE,3=RED")
       int energy = 2                                  (doc = "0=depleted,1=low,2=medium,3=high")
       string altitude = "10k"
       int exercise_recency = 0
       string sleep_quality = "unknown"
       string context = "desk"
       int building_task_threshold = 3                  (doc = "Tunable: tasks needed for cold_start→building")
       float rolling_coherence_threshold = 0.7          (doc = "Tunable: coherence needed for building→rolling")
       float burst_detection_velocity = 3.0             (doc = "Tunable: velocity for burst detection")
       int burnout_yellow_threshold = 30                (doc = "Tunable: exchanges before YELLOW")
       int tasks_completed = 0
       int exchanges_without_break = 0
       bool frustration_signal = false
       int adrenaline_debt = 0
       bool exogenous_red = false
       float exchange_velocity = 0.0
       float topic_coherence = 0.5
       float wall_clock_delta = 0.0
       float allostatic_load = 0.0
   }
   ```

   **`schemas/injectionPrim.usda`:**
   ```usda
   class "InjectionPrimAPI" (inherits = </APISchemaBase>)
   {
       string profile = "none"
       float s_nm = 0.0
       float alpha = 0.0
       string phase = "baseline"
       int exchange_count = 0
       string routing_mode = "standard"
       float cross_expert_bleed = 0.0
   }
   ```

   **`schemas/anchorPhaseAPI.usda`:**
   ```usda
   class "AnchorPhaseAPI" (inherits = </APISchemaBase>)
   {
       float gain = 1.0    (doc = "ALWAYS 1.0. Structural immunity.")
   }
   ```

   **`schemas/delegatePrim.usda`:**
   ```usda
   class "DelegatePrimAPI" (inherits = </APISchemaBase>)
   {
       string delegate_id = "claude"
       string status = "idle"
       string latency_class = "interactive"
       int raw_context_tokens = 200000
       float compression_factor = 1.0
       int effective_context_tokens = 200000
   }
   ```

2. **Run usdGenSchema:**
   ```bash
   usdGenSchema schemas/cognitiveStatePrim.usda plugins/cognitiveSchema/
   usdGenSchema schemas/injectionPrim.usda plugins/injectionSchema/
   usdGenSchema schemas/anchorPhaseAPI.usda plugins/anchorSchema/
   usdGenSchema schemas/delegatePrim.usda plugins/delegateSchema/
   ```
   This generates C++ classes, Python bindings, plugInfo.json for each schema.

3. **Verify generated code compiles:**
   ```bash
   cd plugins/cognitiveSchema
   cmake . -DUSD_ROOT=/opt/usd-26.03
   make -j$(nproc)
   ```

### Verification:
- usdGenSchema produces C++ files without errors
- Generated code compiles against USD 26
- Python bindings import: `from CognitiveStatePrimAPI import CognitiveStatePrimAPI`
- Schema applies to a prim: `prim.ApplyAPI(CognitiveStatePrimAPI)`

### Gate: Print generated file list + compile result + Python import test. Stop. Await approval.
### Git: `git commit -m "Sprint 2 Phase 1: USDA schemas + usdGenSchema output"`

---

## PHASE 2: C++ Computation Callbacks

### Gate: Phase 1 passed (schemas generated and compiled).

### Tasks:

1. **Write computation callbacks** in the generated plugin directories.

   Each callback:
   - Uses `EXEC_REGISTER_COMPUTATIONS_FOR_SCHEMA(SchemaName)` macro
   - Reads inputs from authored stage attributes (NOT from own output)
   - Reads thresholds from stage attributes (parameterized)
   - Returns computed value
   - Is a pure function (stateless)

   **Reference:** `src/computations/` from Sprint 1 contains the Python logic. The C++ callback must produce identical results for identical inputs.

2. **Key computation: `computeMomentum`** (example pattern for all):
   ```cpp
   #include "pxr/exec/exec/register.h"
   #include "cognitiveStatePrimAPI.h"

   PXR_NAMESPACE_OPEN_SCOPE

   EXEC_REGISTER_COMPUTATIONS_FOR_SCHEMA(CognitiveStatePrimAPI)
   {
       RegisterComputation("computeMomentum",
           [](const auto& inputs) -> int {
               // Read authored values (NOT own output — no cycles)
               int tasks = inputs.Get<int>("tasks_completed");
               float coherence = inputs.Get<float>("topic_coherence");
               float velocity = inputs.Get<float>("exchange_velocity");
               int prev_momentum = inputs.Get<int>("momentum");  // t-1, authored by Bridge
               int energy = inputs.Get<int>("energy");  // computed by computeEnergy

               // Read thresholds from stage (tunable via USDA)
               int building_threshold = inputs.Get<int>("building_task_threshold");
               float rolling_threshold = inputs.Get<float>("rolling_coherence_threshold");

               // State machine logic (must match Sprint 1 MockCogExec exactly)
               if (prev_momentum == 1 && tasks >= building_threshold && energy >= 2) return 2;
               if (prev_momentum == 2 && coherence >= rolling_threshold) return 3;
               // ... full transition table from State Machine Spec §3
               return prev_momentum;  // no transition
           }
       );
   }

   PXR_NAMESPACE_CLOSE_SCOPE
   ```

3. **Anchor immunity** (AnchorPhaseAPI — separate schema, separate callback):
   ```cpp
   EXEC_REGISTER_COMPUTATIONS_FOR_SCHEMA(AnchorPhaseAPI)
   {
       RegisterComputation("computeGain",
           [](const auto& inputs) -> float {
               return 1.0f;  // Unconditional. Always. No inputs evaluated.
           }
       );
   }
   ```

4. **Write ALL computation callbacks:**
   - computeMomentum (CognitiveStatePrimAPI)
   - computeBurnout (CognitiveStatePrimAPI) — with RED event exception
   - computeEnergy (CognitiveStatePrimAPI) — with adrenaline masking
   - computeBurst (CognitiveStatePrimAPI)
   - computeAllostatic (CognitiveStatePrimAPI)
   - computeRouting (CognitiveStatePrimAPI) — outputs capability requirements
   - computePermission (CognitiveStatePrimAPI)
   - computeGain (AnchorPhaseAPI) — always returns 1.0
   - computeGain (InjectionPrimAPI) — g = 1 + s_nm * d
   - computePredictionAudit (CognitiveStatePrimAPI) — compares prediction vs actual

5. **Compile the plugin library:**
   ```bash
   cmake . -DUSD_ROOT=/opt/usd-26.03
   make -j$(nproc)
   ```
   Produces: `libCognitiveExecPlugins.so` (Linux/Mac) or `.dll` (Windows)

### Verification:
- All callbacks compile without warnings
- Plugin library loads in USD: `Plug.Registry().RegisterPlugins(["./plugins/"])`
- Each computation can be invoked via ExecUsdSystem

### Gate: Print compile result + plugin load test. Stop. Await approval.
### Git: `git commit -m "Sprint 2 Phase 2: C++ computation callbacks compiled"`

---

## PHASE 3: ExecUsdSystem Integration

### Gate: Phase 2 passed (plugin compiles and loads).

### Tasks:

1. **Create `src/openexec_bridge.py`** — replaces MockCogExec:
   ```python
   from pxr import Usd, Exec

   class OpenExecBridge:
       """
       Replaces MockCogExec. Uses real OpenExec to evaluate
       cognitive computations against a real USD stage.
       """
       def __init__(self, stage: Usd.Stage):
           self.stage = stage
           self.system = Exec.ExecUsdSystem(stage)

       def evaluate(self, prim_path: str, computation_name: str):
           """Request a computed value via OpenExec."""
           prim = self.stage.GetPrimAtPath(prim_path)
           request = self.system.BuildRequest()
           key = Exec.ExecUsdValueKey(prim, computation_name)
           request.Add(key)
           results = self.system.Compute(request)
           return results.Get(key)

       def evaluate_all(self, prim_path: str):
           """Evaluate all cognitive computations for a prim."""
           prim = self.stage.GetPrimAtPath(prim_path)
           request = self.system.BuildRequest()
           computations = [
               "computeMomentum", "computeBurnout", "computeEnergy",
               "computeBurst", "computeAllostatic", "computeRouting",
               "computePermission"
           ]
           keys = {}
           for comp in computations:
               key = Exec.ExecUsdValueKey(prim, comp)
               request.Add(key)
               keys[comp] = key
           results = self.system.Compute(request)
           return {name: results.Get(key) for name, key in keys.items()}
   ```

2. **Create adapter** that makes OpenExecBridge satisfy the same interface as MockCogExec:
   - Same method signatures
   - Same return types
   - Sprint 1 bridge.py can use either backend via a config flag

3. **Wire into existing bridge.py** with a backend switch:
   ```python
   if config.backend == "openexec":
       engine = OpenExecBridge(usd_stage)
   else:
       engine = MockCogExec(mock_stage)
   ```

### Verification:
- OpenExecBridge evaluates computeMomentum on a test prim
- Results match MockCogExec for the same inputs
- bridge.py works with both backends

### Gate: Print side-by-side comparison (MockCogExec vs OpenExec) for 10 test cases. Stop. Await approval.
### Git: `git commit -m "Sprint 2 Phase 3: OpenExecBridge integrated"`

---

## PHASE 4: Parity Verification (The Contract)

### Gate: Phase 3 passed.

### Purpose:
Run ALL 84 Sprint 1 tests against the OpenExec backend. Every test must produce identical results. This is the contract: same inputs → same outputs.

### Tasks:

1. **Create `tests/test_sprint2/test_openexec_parity.py`:**
   - For each Sprint 1 computation test, run the same inputs through both MockCogExec and OpenExecBridge
   - Assert results are identical
   - Cover all computations, all edge cases, all boundary conditions

2. **Run the full parity suite:**
   ```bash
   python -m pytest tests/test_sprint2/test_openexec_parity.py -v
   ```

3. **Run the Sprint 1 tests with OpenExec backend:**
   ```bash
   COGTWIN_BACKEND=openexec python -m pytest tests/test_sprint1/ -v
   ```

4. **Verify anchor immunity in native OpenExec:**
   - AnchorPhaseAPI.computeGain returns 1.0 for ALL injection profiles
   - No code path from InjectionPrimAPI attributes to AnchorPhaseAPI computation

5. **Verify no cycles:**
   - OpenExec's cycle detector does not abort during any computation
   - Time-sampled t-1 reads work correctly

### Verification:
```bash
# All three must pass:
python -m pytest tests/test_sprint1/ -v                              # Sprint 1 (MockCogExec)
python -m pytest tests/test_sprint2/test_openexec_parity.py -v       # Parity
COGTWIN_BACKEND=openexec python -m pytest tests/test_sprint1/ -v     # Sprint 1 on OpenExec
```

### Gate: Print test results for all three suites. Stop. Await approval.
### Git: `git commit -m "Sprint 2 Phase 4: 84/84 parity tests passing on OpenExec"`

---

## PHASE 5: Cutover + Cleanup

### Gate: Phase 4 passed (100% parity).

### Tasks:

1. **Set OpenExec as default backend** in bridge.py config
2. **Rename MockCogExec → mock_cogexec_legacy.py** (keep for reference, not imported)
3. **Update AGENTS.md** to reflect Sprint 2 completion
4. **Run full test suite** (84 Sprint 1 + parity + 890 existing):
   ```bash
   python -m pytest tests/ -v
   ```
5. **Document the build** — capture exact build flags, platform, versions in `docs/OPENEXEC_BUILD.md`

### Verification:
- OpenExec is the default backend
- All tests pass
- No MockCogExec imports remain in production code
- Build documented

### Gate: Print full test suite results. Stop.
### Git: `git commit -m "Sprint 2 Phase 5: OpenExec native — MockCogExec retired"`

---

## DIRECTORY STRUCTURE (Sprint 2 additions)

```
Cognitive_Twin/
├── schemas/                              # NEW — USDA schema definitions
│   ├── cognitiveStatePrim.usda
│   ├── injectionPrim.usda
│   ├── anchorPhaseAPI.usda
│   └── delegatePrim.usda
├── plugins/                              # NEW — Generated + compiled C++ plugins
│   ├── cognitiveSchema/
│   ├── injectionSchema/
│   ├── anchorSchema/
│   └── delegateSchema/
├── src/
│   ├── openexec_bridge.py               # NEW — Real OpenExec evaluator
│   ├── mock_cogexec.py → _legacy.py     # RENAMED — kept for reference
│   └── [all Sprint 1 files unchanged]
├── tests/
│   ├── test_sprint1/                     # UNCHANGED — now runs against OpenExec too
│   └── test_sprint2/                     # NEW — parity tests
│       └── test_openexec_parity.py
└── docs/
    └── OPENEXEC_BUILD.md                 # NEW — build documentation
```

---

## BINARY GATES

| Phase | Gate | Approval Signal |
|-------|------|-----------------|
| 0 | USD 26 + OpenExec builds and imports | "Approved. Phase 1." |
| 1 | usdGenSchema output compiles | "Approved. Phase 2." |
| 2 | C++ plugin library compiles and loads | "Approved. Phase 3." |
| 3 | OpenExecBridge evaluates computations correctly | "Approved. Phase 4." |
| 4 | 84/84 parity tests pass | "Approved. Phase 5." |
| 5 | Full cutover, all tests green | "Sprint 2 complete." |

---

## CIRCUIT BREAKER: THE BUILD FAILS

If Phase 0 fails after 3 attempts:

**This is expected and acceptable.** OpenExec is 4 days old in the wild (USD v26.03 shipped March 26, 2026). Non-Pixar developers building it from source is uncharted territory.

**Fallback:** Sprint 1 MockCogExec continues to serve. The architecture is OpenExec-native. The implementation catches up when:
- Pixar ships pre-built wheels with OpenExec
- Community Docker images with OpenExec emerge
- A subsequent USD release stabilizes the build

**Do not treat a build failure as a project failure.** The cognitive twin works today on MockCogExec. OpenExec is the upgrade, not the requirement.

---

## INITIATION PROMPT

```
Read AGENTS.md. This is Sprint 2: Native OpenExec.
Acknowledge the CONSTITUTION and COMMANDMENTS.
Execute Phase 0: USD 26 Build Environment.
Determine platform (Windows or macOS).
Attempt the headless build with OpenExec.
Stop and report build status. If it fails, surface the exact error.
Do NOT proceed past Phase 0 without approval.
```

---

*AGENTS.md — Cognitive Twin Sprint 2*
*Native OpenExec: The Hard Architecture Move*
*Joseph O. Ibrahim | March 2026*
