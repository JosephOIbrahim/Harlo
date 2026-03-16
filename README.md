# Cognitive Twin

A persistent cognitive layer that sits between you and any LLM, modeling not what you know — but how you think.

## The Problem

LLM conversations are stateless. Every session starts from zero. Your context, your patterns of thought, your evolving understanding — all evaporated the moment the window closes. Current "memory" solutions bolt on vector databases that store what you said, not how you reason. The Cognitive Twin inverts this: it builds a living model of your cognition that any LLM can consult, verify against, and evolve through.

## How It Works

```
                          COGNITIVE TWIN v7.0
                          ====================

  You ──► CLI (Click) / MCP (5 tools)
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  BRAINSTEM (Lossless Translation + Metacognitive Routing)      │
  │                                                                │
  │  query ──► Semantic Recall ──► Surprise Z-score ──► Route      │
  │               │                    │                            │
  │               │          System 1 (fast)  System 2 (deliberate) │
  │               ▼                    ▼                            │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  ASSOCIATION ENGINE  │     │  ALETHEIA VERIFICATION   │     │
  │  │  (Right Hemisphere)  │     │  (GVR Loop, max 3)       │     │
  │  │                      │     │                          │     │
  │  │  Rust (PyO3)         │     │  Verify ──► Revise ──►┐  │     │
  │  │  2048-bit SDR encode │     │    ▲                  │  │     │
  │  │  XOR + popcount kNN  │     │    └──────────────────┘  │     │
  │  │  Lazy decay on read  │     │                          │     │
  │  │  <2ms hot recall     │     │  Spec-gaming detection   │     │
  │  └──────────────────────┘     │  Trace-excluded verify   │     │
  │               │               │  UNPROVABLE with dignity │     │
  │               ▼               └──────────────────────────┘     │
  │  ┌──────────────────────┐                    │                 │
  │  │  COMPOSITION ENGINE  │          ┌─────────┴─────────┐       │
  │  │  (Left Hemisphere)   │          │  MOTOR CORTEX     │       │
  │  │                      │          │                   │       │
  │  │  Merkle stages       │          │  Premotor plan    │       │
  │  │  LIVRPS resolution   │          │  Basal Ganglia    │       │
  │  │  Structured          │          │  (5-check gate,   │       │
  │  │    Provenance        │          │   inhibit-default)│       │
  │  └──────────────────────┘          │  ONE action/cycle │       │
  │                                    └───────────────────┘       │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  HEBBIAN ENGINE      │     │  INQUIRY ENGINE (DMN)    │     │
  │  │                      │     │                          │     │
  │  │  Dual-mask SDR       │     │  Pattern detection       │     │
  │  │    evolution         │     │  Apophenia guard         │     │
  │  │  Episodic context    │     │  Sincerity gate          │     │
  │  │    reconstruction    │     │  Rupture & repair        │     │
  │  │  Homeostatic [3%-5%] │     │  Crystallization         │     │
  │  │  Training data       │     │  DMN teardown (<50ms)    │     │
  │  │    pipeline          │     │                          │     │
  │  └──────────────────────┘     └──────────────────────────┘     │
  │                                                                │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  USD-LITE CONTAINER  │     │  COGNITIVE PROFILE       │     │
  │  │                      │     │                          │     │
  │  │  17 typed prim       │     │  Adaptive intake         │     │
  │  │    dataclasses       │     │  Continuous [0,1] scoring│     │
  │  │  .usda serialization │     │  Personal baselines      │     │
  │  │  Hex SDR (512 chars) │     │  Skills observer         │     │
  │  └──────────────────────┘     └──────────────────────────┘     │
  └─────────────────────────────────────────────────────────────────┘
           │
           ▼
  Response (verified, contextual, personally calibrated)
```

The system is event-driven and socket-activated. It idles at 0 watts. No polling, no `sleep()`, no background threads. The daemon wakes on command, does its work, and exits.

### Module Hierarchy

The v7.0 architecture as a dependency graph. The Brainstem is the central translation layer — every subsystem reads and writes through it via USD-Lite stages.

```mermaid
graph TD
    USER["User / MCP Client"] --> CLI["CLI / MCP Server\n5 tools"]
    CLI --> BS["BRAINSTEM\nLossless Translation\n+ Metacognitive Routing"]

    BS --> USD["USD-LITE STAGE\n17 typed prim dataclasses\n.usda serialization"]

    BS --> HIPP["HIPPOCAMPUS\n(Rust / PyO3)\nSDR encode\nXOR + popcount\n< 2ms recall"]

    BS --> ROUTE{"Surprise\nZ-score"}
    ROUTE -->|"z <= threshold"| SYS1["SYSTEM 1\nAssociation Engine\nFast hamming search"]
    ROUTE -->|"z > threshold"| SYS2["SYSTEM 2\nComposition Engine\nLIVRPS + Merkle resolve"]

    SYS1 --> USD
    SYS2 --> USD

    BS --> ALE["ALETHEIA\nGVR verification\nSpec-gaming detection\nTrace-excluded"]
    BS --> MOTOR["MOTOR CORTEX\nBasal Ganglia gate\nInhibit-default\n5-check gate"]
    BS --> DMN["INQUIRY / DMN\nPattern detection\nCo-evolution spiral"]

    USD --> HEBB["HEBBIAN ENGINE\nDual-mask SDR evolution\nEpisodic reconstruction\nTraining data pipeline"]
    USD --> SKILLS["SKILLS OBSERVER\nIncremental cursor\nGrowth arcs\nGap detection"]
    USD --> PROFILE["COGNITIVE PROFILE\nAdaptive intake\nPersonal multipliers\nContinuous scoring"]

    BS --> PROV["PROVENANCE\n5 source types\nDeterministic hashing"]

    HEBB -->|"[V] Variant layer"| USD
    SKILLS -->|"Ghost window\nO(new_traces)"| USD
    PROFILE -->|"Calibrates thresholds"| ROUTE

    style BS fill:#4a9eff,color:#fff
    style USD fill:#0d1117,color:#c9d1d9,stroke:#30363d
    style HIPP fill:#d4380d,color:#fff
    style ROUTE fill:#9a6700,color:#fff
    style SYS1 fill:#2ea043,color:#fff
    style SYS2 fill:#6e40c9,color:#fff
    style HEBB fill:#cf222e,color:#fff
    style ALE fill:#1f6feb,color:#fff
```

### Generation Pipeline

How a query flows through the system end-to-end:

```mermaid
flowchart TD
    Q["Query"] --> R["Semantic Recall\nSDR encode + XOR kNN\n< 2ms"]
    R --> S{"Surprise\nZ-score"}
    S -->|"z <= threshold\n(System 1)"| INJ["Context Injection"]
    S -->|"z > threshold\n(System 2)"| ESC["Escalate to Composition\nLIVRPS + Merkle resolve"]
    ESC --> INJ
    INJ --> LLM["LLM Generation\nProvider API call"]
    LLM --> AMY{"Amygdala\ntrigger?"}
    AMY -->|"Safety / Consent"| REF["1-shot Permanent Reflex\nSkip GVR entirely"]
    AMY -->|No| GVR["Aletheia GVR Loop"]
    GVR --> V{"Verdict?"}
    V -->|VERIFIED| CONS["Consolidate + Reflex cache"]
    V -->|SPEC_GAMED| SGOUT["Return to user\nnever consolidate"]
    V -->|"FIXABLE\ncycle < 3"| REV["Revise output"] --> GVR
    V -->|UNPROVABLE| PARK["Park with dignity\nreason + what_would_help"]
    CONS --> HEBB["Hebbian Update\nCo-activation + Dual masks"]
    HEBB --> RESP["Response\nverified + contextual + confidence"]
    PARK --> RESP
    REF --> RESP
    SGOUT --> RESP

    style Q fill:#4a9eff,color:#fff
    style RESP fill:#2ea043,color:#fff
    style REF fill:#d4380d,color:#fff
    style SGOUT fill:#cf222e,color:#fff
    style PARK fill:#9a6700,color:#fff
```

### Aletheia Verification States

The Generate-Verify-Revise loop and its four terminal states:

```mermaid
stateDiagram-v2
    [*] --> Verify: intent + output\n(reasoning_trace = None)

    Verify --> VERIFIED: Sound and\nanswers original intent
    Verify --> SPEC_GAMED: Correct answer\nwrong question
    Verify --> FIXABLE: Detectable flaw

    FIXABLE --> Revise: cycle < 3
    Revise --> Verify: patched output
    FIXABLE --> UNPROVABLE: cycle >= 3\n(ADHD guard)

    VERIFIED --> [*]: Consolidate to reflex
    SPEC_GAMED --> [*]: Return — never consolidate
    UNPROVABLE --> [*]: Park with metadata\n(reason, what_would_help, partial_progress)

    note right of Verify: Rule 11 — verifier NEVER\nsees reasoning traces
    note right of SPEC_GAMED: Rule 15 — dominant failure mode\ndetected via topic drift + deflection
    note left of UNPROVABLE: Rule 16 — first-class state\nwith dignity, not silent drop
```

### Trace Lifecycle

The full journey of a memory trace — from storage through encoding, recall, Hebbian evolution, reconstruction, and eventual apoptosis. The reconsolidation boost creates a feedback loop that saves degraded traces from death when users actually retrieve their reconstructed episodes.

```mermaid
flowchart TD
    STORE["Store\nmessage + domain + tags"] --> ENCODE["Encode\nBGE-small-en-v1.5\n384-dim embedding"]
    ENCODE --> LSH["LSH Projection\ntop-80 bits active"]
    LSH --> SDR["2048-bit SDR\nhex-packed (512 chars)"]
    SDR --> DB[("SQLite\ntwin.db\nbase SDR pristine")]

    DB -->|"Query arrives"| RECALL["Recall\nXOR + popcount\nHamming distance\n< 2ms"]
    RECALL --> ZSCORE{"Surprise\nZ-score =\n(hamming - mean)\n/ max(std, 1.0)"}
    ZSCORE -->|"z <= threshold\nSystem 1"| FAST["Fast Return\nAssociation only"]
    ZSCORE -->|"z > threshold\nSystem 2"| DELIBERATE["Escalate\nComposition LIVRPS\n+ Merkle resolve"]

    RECALL -->|"Top-K co-fire"| COACT["Co-activation\ntrace_a.co_activations[b] += 1"]
    RECALL -->|"Domain conflict"| COMPETE["Competition\ntrace_a.competitions[b] += 1"]

    COACT --> STRENGTHEN["Hebbian Strengthen\nP(set) = alpha * (count / max)\nBits added to strengthen_mask"]
    COMPETE --> WEAKEN["Anti-Hebbian Weaken\nP(clear) = beta * (count / max)\nBits added to weaken_mask"]

    STRENGTHEN --> VARIANT["[V] Variant Layer\neffective = (base | str) & ~wk\nConflict: weaken wins"]
    WEAKEN --> VARIANT
    VARIANT --> HOMEO{"Homeostatic\nPlasticity"}
    HOMEO -->|"density < 3%"| UNDO_W["Undo weakening"]
    HOMEO -->|"3% - 5%"| OK["Within band"]
    HOMEO -->|"density > 5%"| UNDO_S["Undo strengthening"]

    DB -->|"On read\nRule 4: lazy"| DECAY{"Decay\nstrength = init * e^(-kt)\n+ retrieval_boosts\n+ hebbian_boosts"}
    DECAY -->|"strength >= epsilon"| ALIVE["Alive\nreturn in results"]
    DECAY -->|"epsilon < strength\n< recon_threshold"| RECON["Episodic\nReconstruction"]
    DECAY -->|"strength < epsilon"| APO["Apoptosis\nDELETE + VACUUM\nDB shrinks"]

    RECON --> PULL["Pull top-N\nHebbian-linked traces"]
    PULL --> COMPOSE["LIVRPS compose\nreconstructed episode"]
    COMPOSE --> MARK["Mark reconstructed: true\nprovenance: HEBBIAN_DERIVED\ncontributing_traces: [ids]"]
    MARK -->|"Surfaced to user?"| DECISION{"User-facing\nretrieval?"}
    DECISION -->|"Yes"| BOOST["Reconsolidation\nBoost +0.1\nto all contributors"]
    DECISION -->|"No (internal only)"| NOOP["No boost\ntraces cannot\nself-bootstrap"]
    BOOST -->|"Saves fragments\nfrom apoptosis"| DB

    style DB fill:#0d1117,color:#c9d1d9,stroke:#30363d
    style APO fill:#d4380d,color:#fff
    style ALIVE fill:#2ea043,color:#fff
    style RECON fill:#9a6700,color:#fff
    style BOOST fill:#1f6feb,color:#fff
    style VARIANT fill:#6e40c9,color:#fff
    style ZSCORE fill:#4a9eff,color:#fff
    style NOOP fill:#6e7681,color:#fff
```

### Motor Cortex Decision Gate

Inhibition-default: every action must pass ALL five checks or it's blocked.

```mermaid
flowchart TD
    ACT["Planned Action"] --> BG{"BASAL GANGLIA GATE\n(default: INHIBIT ALL)"}
    BG --> C1["Anchor alignment"]
    BG --> C2["Consent level"]
    BG --> C3["Aletheia verified"]
    BG --> C4["Reversibility"]
    BG --> C5["Scope boundaries"]

    C1 & C2 & C3 & C4 & C5 --> CHK{"All 5 pass?"}

    CHK -->|"All pass"| DIS["DISINHIBIT\nExecute ONE action"]
    CHK -->|"Consent insufficient"| ESC["ESCALATE\nRequest higher consent"]
    CHK -->|"Level 3 detected"| LOCK["LOCKED\nGate welded shut\n(financial / irreversible / others' data)"]
    CHK -->|"Any other failure"| INH["INHIBIT\nAction blocked"]

    DIS --> LOOP["Return to full\ncognitive loop\n(Rule 24: one action at a time)"]

    INH -.->|"Even cached reflexes\nre-check every time\n(Rule 26)"| BG

    style BG fill:#d4380d,color:#fff
    style DIS fill:#2ea043,color:#fff
    style LOCK fill:#6e40c9,color:#fff
    style INH fill:#cf222e,color:#fff
    style ESC fill:#9a6700,color:#fff
```

### Co-Evolution Spiral

How the Twin and the human transform each other through interaction:

```mermaid
sequenceDiagram
    participant H as Human
    participant T as Twin (Brainstem)
    participant A as Aletheia
    participant D as DMN (Inquiry)

    H->>T: "I'm a decisive person"
    T->>T: Store trace (self_reported)
    T->>A: Verify in Composition
    A->>A: Evidence shows 12 deferred decisions
    A-->>T: Emit perception_gap trace

    T->>D: DMN synthesis window (<=30s)
    D->>D: Apophenia guard: 12 obs >= 8 threshold
    D->>D: Alt hypothesis: "maybe only in high-stakes"
    D->>H: "You describe yourself as decisive, but I see<br/>12 deferred decisions this month. What's your read?"

    alt Sincere engagement
        H->>T: "Huh — I think I defer on things I don't care about"
        T->>T: Both learn. Model refines.
        Note over T: Trace updated: decisive on high-stakes,<br/>delegates low-stakes
    else Rejection
        H->>T: "That's not right"
        T->>T: Permanent rejection trace (weight 2.0)
        Note over T: 3 rejections -> offer to stop asking<br/>90-day half-life -> gently retry later
    else Blind spot acceptance (Rule 33)
        H->>T: "I know. I'm okay with that."
        T->>T: Tag: blind_spot_accepted
        Note over T,A: Aletheia keeps objective truth internally<br/>DMN never raises this specific claim again
        Note over T: "The Twin chooses the relationship<br/>over the truth"
    end
```

## Key Design Decisions

**1-bit SDR bitvectors, not float embeddings.** Memory search uses 2048-bit Sparse Distributed Representations. Hamming distance via XOR + popcount. No cosine similarity, no float32 storage. The Rust hot path processes these at <2ms for recall.

**USD-Lite container format.** Every subsystem writes to a shared USD stage with 17 typed prim dataclasses. `.usda` text serialization with proven round-trip fidelity. LIVRPS composition with permanent-prim handling. Float tolerance via `math.isclose()`. SDR arrays packed as 512-char hex strings (not 6KB text arrays).

### LIVRPS Composition Precedence

Pixar's USD composition ordering adapted for brain state. Strongest opinion wins per attribute. Permanent prims (Amygdala reflexes) override everything.

```mermaid
graph LR
    L["[L] LOCAL\nStrongest\nDirect opinion"]
    I["[I] INHERIT\nInherited from\nparent prim"]
    V["[V] VARIANT\nHebbian deltas\n(dual masks)"]
    R["[R] REFERENCE\nExternal data\npointer"]
    P["[P] PAYLOAD\nAttached data"]
    S["[S] SUBLAYER\nWeakest\nSQLite projection"]

    L -->|"overrides"| I
    I -->|"overrides"| V
    V -->|"overrides"| R
    R -->|"overrides"| P
    P -->|"overrides"| S

    PERM["PERMANENT\n(Amygdala reflex)\nOverrides all\narc types"]

    PERM -.->|"always wins"| L

    TIE["Same arc type?\nLater timestamp wins"]

    style L fill:#d4380d,color:#fff
    style S fill:#6e7681,color:#fff
    style PERM fill:#6e40c9,color:#fff
    style V fill:#9a6700,color:#fff
    style TIE fill:#0d1117,color:#c9d1d9,stroke:#30363d
```

**Brainstem lossless translation.** Each subsystem gets one adapter pair (native to/from USD prims). Round-trip fidelity proven by Hypothesis property-based testing. Z-score surprise metric drives dual-process routing: System 1 (fast hamming search) escalates to System 2 (deliberative LIVRPS) when surprise exceeds the user's personal threshold.

**Dual-mask Hebbian learning (not XOR).** Co-activated traces strengthen shared bits; competing traces weaken them. Separate `strengthen_mask` and `weaken_mask` stored in the [V] Variant USD layer. Formula: `effective_sdr = (base | strengthen) & ~weaken`. Conflict resolution: weaken wins. Base SDR in SQLite stays pristine. Merkle hash computed over base traces only. Homeostatic plasticity clamps activation density to [3%, 5%].

**Episodic context reconstruction.** Degraded traces below the reconstruction threshold are rebuilt from Hebbian-linked co-activations via LIVRPS composition. The apoptosis clamp (`max(apoptosis + 0.05, threshold)`) prevents the race condition where traces die before qualifying for reconstruction. Reconsolidation boost fires only on user-facing retrieval — traces cannot bootstrap their own survival.

**Cognitive profile intake.** An adaptive neuropsych-informed questionnaire calibrates personal thresholds. Continuous [0.0, 1.0] scoring with deterministic linear interpolation. Semantic ceiling detection (not answer length). The Twin works from the first interaction with universal defaults; the intake makes it work *better*.

**Lazy decay, not polling.** Trace strength is computed on retrieval: `strength = initial * e^(-lambda * dt) + sum(boosts) + sum(hebbian_boosts)`. No background jobs. Traces below epsilon are physically deleted (apoptosis) with `VACUUM` — the database actually shrinks.

**Aletheia verification pipeline.** Every LLM response runs through Generate-Verify-Revise. Max 3 cycles (ADHD guard). The verifier never sees reasoning traces (structural constraint). Spec-gaming detection catches correct answers to wrong questions. Unresolvable outputs are parked as UNPROVABLE with full metadata — not silently dropped.

**Inhibition-default motor cortex.** The Basal Ganglia gate defaults to INHIBIT ALL. Every action requires all five checks (anchor, consent, verification, reversibility, scope). Financial transactions and irreversible deletions are structurally locked. RED state halts everything.

**Structured provenance.** Every composition layer carries a typed Provenance dataclass (source_type, origin_timestamp, event_hash, session_id). Five source types: USER_DIRECT, EXTERNAL_REFERENCE, SYSTEM_INFERRED, HEBBIAN_DERIVED, INTAKE_CALIBRATED. Legacy layers receive SYSTEM_INFERRED during migration.

**Aletheia training data pipeline.** Every verification event appends a JSONL row with the full cognitive profile feature vector (not just a hash). O(1) amortized log rotation at 10,000 rows. No reasoning traces (Rule 11). Ready for LoRA fine-tuning of a personalized verification model.

## Quick Start

```bash
git clone <repo-url> && cd cognitive-twin

# Python environment
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .
pip install anthropic sentence-transformers

# Build Rust hot path (optional — system falls back to Python encoding)
pip install maturin
maturin develop -r

# Download the semantic encoder model (~130MB, one-time)
python scripts/setup_semantic_encoder.py

# Set your LLM provider key
export ANTHROPIC_API_KEY="sk-ant-..."

# First question
python -m cognitive_twin.cli.main ask "What patterns do you notice in my recent traces?"
```

## Project Structure

```
python/cognitive_twin/
├── aletheia/          Verification engine — GVR loop, spec-gaming, trace exclusion
├── brainstem/         Lossless translation — adapters, routing, generation pipeline,
│                        amygdala, consolidation, provenance, escalation
├── cli/               Click CLI — human + JSON output
│   └── commands/      Individual command implementations
├── composition/       Left hemisphere — Merkle stages, LIVRPS resolution, audit trail
├── daemon/            Socket-activated daemon — router, config, lifecycle
├── encoder/           Dual-path encoding — semantic (BGE+LSH) and lexical (Rust n-gram)
├── hebbian/           Neuroplasticity — dual-mask SDR evolution, reconstruction,
│                        training data pipeline
├── inquiry/           Default Mode Network — pattern surfacing, safeguards, co-evolution
├── intake/            Cognitive profile — adaptive questionnaire, multiplier derivation
├── modulation/        Brainstem — allostatic load, gain, barrier, pattern detection
├── motor/             Motor cortex — premotor planning, Basal Ganglia gate, executor
├── provider/          LLM abstraction — Protocol-based, Claude and OpenAI adapters
├── session/           Session lifecycle — SQLite-backed, history, expiration
├── skills/            Competence tracking — incremental observer, 4 query patterns
├── usd_lite/          USD container — 17 prim dataclasses, .usda serialization, LIVRPS
└── migrate_v7.py      v6 → v7 migration (bootstraps /Skills from legacy traces)

crates/hippocampus/    Rust hot path — SDR encode, XOR search, lazy decay, apoptosis
config/                Barrier schema, verification depth, default profile
data/                  Runtime data — stages, reflexes, audit, training data
scripts/               Daemon start/stop, model download
tests/                 20 test modules across all subsystems
```

## Testing

**761 tests** (720 Python + 41 Rust), all passing.

```bash
pytest tests/ -v                                  # Full Python suite (720)
cargo test -p hippocampus                         # Rust tests (41)
pytest tests/test_integration/ -v                 # Integration + compliance

# Phase-specific verification
pytest tests/test_usd_lite/ -v                    # USD container format
pytest tests/test_brainstem/ -v                   # Lossless translation + routing
pytest tests/test_skills/ -v                      # Incremental skills observer
pytest tests/test_intake/ -v                      # Cognitive profile intake
pytest tests/test_hebbian/ -v                     # Hebbian + reconstruction + training data
```

Coverage spans: USD serialization round-trip, hex SDR encoding, LIVRPS composition, adapter fidelity (Hypothesis property-based), Z-score surprise routing, Merkle isolation, dual-mask Hebbian correctness, homeostatic stability, episodic reconstruction, apoptosis clamp, reconsolidation boost gating, training data JSONL, O(1) log rotation, cognitive profile continuous scoring, semantic ceiling detection, incremental skills observation, GVR protocol, spec-gaming detection, Basal Ganglia gating, structured provenance, and compliance with all 33 architectural rules.

## Research Alignment

| Research Concept | Implementation | Status |
|---|---|---|
| SSGM temporal decay | Lazy decay with Hebbian boost integration | Extended |
| SSGM pre-consolidation validation | Aletheia trace exclusion (blinded) | Already ahead |
| SSGM provenance | Structured 5-type Provenance dataclass | **New in v7** |
| SSGM fragment reconstruction | Episodic reconstruction via Hebbian + LIVRPS | **New in v7** |
| Titans test-time memorization | Hebbian dual-mask SDR evolution | **New in v7** |
| Titans forgetting gate | Apoptosis (more aggressive, with clamp) | Already ahead |
| Mnemis entropy gating | Z-score surprise metric + dual-process routing | **New in v7** |
| HiMem reconsolidation | Brain-wide LIVRPS + reconsolidation boost | Extended |
| LoCoMo-Plus Level-2 memory | Skills observer + competence tracking | **New in v7** |
| Analog I sovereign refusal | Basal Ganglia inhibition-default gate | Already ahead |
| (No equivalent in literature) | Cognitive Profile intake system | **Original** |

## MCP Quick Reference

The Cognitive Twin exposes 5 tools via [Model Context Protocol](https://modelcontextprotocol.io). Works with Claude Desktop, Claude Code, and any MCP-compatible client.

### `twin_store` — Save a memory trace

```
twin_store(message, domain?, tags?)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `message` | string | yes | `"Resolved Python 3.12 path issue by installing mcp into PATH Python"` |
| `domain` | string | no | `"technical"`, `"debugging"`, `"architecture"`, `"decision"` |
| `tags` | string[] | no | `["mcp", "python-path", "resolved"]` |

### `twin_recall` — Semantic search over stored traces

```
twin_recall(query, depth?)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `query` | string | yes | `"Python import issues"` |
| `depth` | `"normal"` \| `"deep"` | no | `"normal"` (top 5) or `"deep"` (top 15) |

Returns matching traces ranked by SDR hamming distance with strength scores and confidence.

### `twin_ask` — Full generation pipeline

```
twin_ask(question)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `question` | string | yes | `"What problems did I hit getting MCP working?"` |

Pipeline: semantic recall + Z-score routing + context injection + LLM generation + Aletheia GVR verification + response.

> Requires `ANTHROPIC_API_KEY` in the server environment.

### `twin_patterns` — Detect clusters and escalation

```
twin_patterns()
```

No arguments. Runs all detection algorithms:
- **Recurring themes** — semantic clustering via SDR hamming distance
- **Temporal patterns** — trace co-occurrence within 24h windows
- **Allostatic load** — escalation tracking across sessions

### `twin_session_status` — Active session info

```
twin_session_status()
```

No arguments. Returns active sessions with exchange count, allostatic load, domain, and timing.

### Setup

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cognitive-twin": {
      "command": "cognitive-twin",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### How It Works

- **Encoder**: BGE embeddings + LSH -> 2048-bit Sparse Distributed Representations
- **Container**: USD-Lite with 17 typed prim dataclasses + `.usda` serialization
- **Search**: XOR + popcount (Hamming distance) — sub-2ms recall
- **Routing**: Z-score surprise metric -> System 1 / System 2 dual-process
- **Learning**: Dual-mask Hebbian SDR evolution with homeostatic plasticity
- **Decay**: Lazy (computed on read, not background jobs)
- **Verification**: Aletheia GVR loop (trace-excluded, max 3 cycles)
- **Hot path**: Rust via PyO3 (`hippocampus` crate)

## The 33 Rules

The architecture is constrained by 33 inviolable rules covering biological fidelity (0W idle, 1-bit SDRs, lazy decay), verification integrity (trace exclusion, max 3 GVR cycles, verified-only consolidation), inquiry safeguards (apophenia guard, sincerity gate, rupture & repair), motor safety (inhibition default, one action at a time, RED kills everything), and Hebbian constraints (Merkle isolation, dual masks not XOR, homeostatic plasticity). These aren't guidelines — they're structural constraints enforced by 761 tests. See `CLAUDE.md` for the full specification.

## Philosophy

The Cognitive Twin is a self-evolving dialogue between a human and their externalized cognition, where both participants transform through the interaction, and the intelligence lives in the relationship — not in either party alone.

You own your mind. AI models just rent access to it.

## License

Proprietary. Copyright Joseph O. Ibrahim, 2026.
