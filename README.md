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
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed', 'secondaryColor': '#16213e', 'tertiaryColor': '#0f3460'}}}%%
graph TB
    CLI["CLI · Click"]:::entry
    MCP["MCP Server · 5 Tools"]:::entry
    DAEMON["Daemon\nSocket-activated · 0W idle"]:::core

    CLI --> DAEMON
    MCP --> DAEMON

    subgraph BRAINSTEM["🧠 BRAINSTEM · Lossless Translation Layer"]
        direction TB
        ADAPT["Adapter Pairs\nnative ↔ USD prims"]:::brainstem
        ROUTE["Z-Score Surprise Router\nSystem 1 / System 2"]:::brainstem
        GEN["Generation Pipeline"]:::brainstem
        PROV["Structured Provenance\n5 source types"]:::brainstem
        AMYG["Amygdala Reflexes\npermanent prims"]:::brainstem
        CONSOL["Consolidation"]:::brainstem
        ESCAL["Escalation"]:::brainstem

        ADAPT --> ROUTE
        ROUTE --> GEN
        GEN --> PROV
    end

    DAEMON --> BRAINSTEM

    subgraph RIGHT["Association Engine · Right Hemisphere"]
        direction TB
        ENC["Encoder\nBGE + LSH → 2048-bit SDR"]:::right
        RUST["Rust Hot Path · PyO3\nXOR + popcount kNN\n< 2ms recall"]:::right
        DECAY["Lazy Decay\ncomputed on read"]:::right
        ENC --> RUST --> DECAY
    end

    subgraph LEFT["Composition Engine · Left Hemisphere"]
        direction TB
        MERKLE["Merkle Stages\nisolated hash trees"]:::left
        LIVRPS["LIVRPS Resolution\nstrongest opinion wins"]:::left
        AUDIT["Audit Trail"]:::left
        MERKLE --> LIVRPS --> AUDIT
    end

    subgraph ALETHEIA["Aletheia Verification"]
        direction TB
        GVR["GVR Loop\nmax 3 cycles"]:::verify
        SPEC["Spec-Gaming Detection"]:::verify
        TRACE_EX["Trace-Excluded Verify\nblinded verifier"]:::verify
        UNPR["UNPROVABLE\nwith dignity"]:::verify
        GVR --> SPEC
        GVR --> TRACE_EX
        GVR --> UNPR
    end

    subgraph MOTOR["Motor Cortex"]
        direction TB
        PREMOTOR["Premotor Planning"]:::motor
        BG["Basal Ganglia Gate\n5-check · inhibit-default"]:::motor
        EXEC["Executor\nONE action/cycle"]:::motor
        PREMOTOR --> BG --> EXEC
    end

    subgraph HEBBIAN["Hebbian Engine"]
        direction TB
        DUAL["Dual-Mask SDR Evolution\nstrengthen + weaken"]:::hebbian
        RECON["Episodic Reconstruction\nvia co-activations"]:::hebbian
        HOMEO["Homeostatic Plasticity\n3%–5% density"]:::hebbian
        TRAIN["Training Data Pipeline\nJSONL · O(1) rotation"]:::hebbian
        DUAL --> RECON
        DUAL --> HOMEO
        DUAL --> TRAIN
    end

    subgraph INQUIRY["Inquiry Engine · DMN"]
        direction TB
        PATTERN["Pattern Detection"]:::inquiry
        APOPH["Apophenia Guard"]:::inquiry
        SINC["Sincerity Gate"]:::inquiry
        RUPTURE["Rupture & Repair"]:::inquiry
        CRYSTAL["Crystallization"]:::inquiry
        PATTERN --> APOPH --> SINC
    end

    subgraph USD["USD-Lite Container"]
        direction TB
        PRIMS["17 Typed Prim Dataclasses"]:::usd
        USDA[".usda Serialization\nround-trip fidelity"]:::usd
        HEX["Hex SDR · 512 chars"]:::usd
        PRIMS --> USDA --> HEX
    end

    subgraph PROFILE["Cognitive Profile"]
        direction TB
        INTAKE["Adaptive Intake\nneuropsych-informed"]:::profile
        SCORING["Continuous 0,1 Scoring\nlinear interpolation"]:::profile
        BASELINE["Personal Baselines\nsurprise thresholds"]:::profile
        SKILLS["Skills Observer\n4 query patterns"]:::profile
        INTAKE --> SCORING --> BASELINE
    end

    subgraph SESSION["Session Management"]
        direction TB
        SQLITE["SQLite-Backed"]:::session
        HIST["History Tracking"]:::session
        EXPIRE["Expiration"]:::session
    end

    subgraph PROVIDER["LLM Provider"]
        direction TB
        PROTO["Protocol-Based Interface"]:::provider
        CLAUDE_A["Claude Adapter"]:::provider
        OPENAI_A["OpenAI Adapter"]:::provider
        PROTO --> CLAUDE_A
        PROTO --> OPENAI_A
    end

    %% All subsystems read/write through Brainstem via USD-Lite
    BRAINSTEM <-->|"USD prims"| USD
    BRAINSTEM --> RIGHT
    BRAINSTEM --> LEFT
    BRAINSTEM --> ALETHEIA
    BRAINSTEM --> MOTOR
    BRAINSTEM --> HEBBIAN
    BRAINSTEM --> INQUIRY
    BRAINSTEM --> PROFILE
    BRAINSTEM --> SESSION
    GEN --> PROVIDER

    %% Styles
    classDef entry fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef core fill:#1a1a2e,stroke:#7c3aed,color:#c4b5fd,font-weight:bold
    classDef brainstem fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef right fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef left fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef verify fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc
    classDef motor fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef hebbian fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef inquiry fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef usd fill:#1a2a1a,stroke:#22c55e,color:#bbf7d0
    classDef profile fill:#3a1a4a,stroke:#d946ef,color:#f0abfc
    classDef session fill:#1a1a2e,stroke:#6b7280,color:#9ca3af
    classDef provider fill:#1a1a2e,stroke:#7c3aed,color:#c4b5fd
```

### Generation Pipeline

How a query flows through the system end-to-end:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph LR
    Q["Query"]:::input

    subgraph RECALL["Semantic Recall"]
        direction TB
        ENCODE["BGE + LSH\n→ 2048-bit SDR"]:::recall
        SEARCH["XOR + popcount\nHamming kNN"]:::recall
        MATCH["Top-K Traces\nranked by distance"]:::recall
        ENCODE --> SEARCH --> MATCH
    end

    subgraph SURPRISE["Surprise Scoring"]
        direction TB
        ZSCORE["Z-Score\nvs personal baseline"]:::surprise
        SYS1{"Z < threshold?"}:::decision
        ZSCORE --> SYS1
    end

    subgraph SYSTEM1["System 1 · Fast"]
        direction TB
        ASSOC["Association Engine\nSDR hot recall\n< 2ms"]:::fast
    end

    subgraph SYSTEM2["System 2 · Deliberate"]
        direction TB
        COMPOSE["Composition Engine\nLIVRPS resolution"]:::deliberate
        CONTEXT["Context Injection\nUSD stage merge"]:::deliberate
        LLM["LLM Generation\nClaude / OpenAI"]:::deliberate
        COMPOSE --> CONTEXT --> LLM
    end

    subgraph VERIFY["Aletheia GVR"]
        direction TB
        GEN_V["Generate"]:::verify
        VER_V["Verify\ntrace-excluded"]:::verify
        REV_V["Revise"]:::verify
        SPEC_V["Spec-Gaming\nCheck"]:::verify
        GEN_V --> VER_V
        VER_V -->|"fail · ≤3 cycles"| REV_V --> GEN_V
        VER_V --> SPEC_V
    end

    subgraph GATE["Motor Cortex"]
        direction TB
        BG_V["Basal Ganglia\n5-check gate"]:::gate
    end

    RESP["Verified Response\ncontextual · calibrated"]:::output

    Q --> RECALL --> SURPRISE
    SYS1 -->|"yes · familiar"| SYSTEM1
    SYS1 -->|"no · surprising"| SYSTEM2
    SYSTEM1 --> VERIFY
    SYSTEM2 --> VERIFY
    VER_V -->|"pass"| GATE --> RESP

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef output fill:#22c55e,stroke:#4ade80,color:#fff,font-weight:bold
    classDef recall fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef surprise fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef decision fill:#4a3a1a,stroke:#f59e0b,color:#fde68a,font-weight:bold
    classDef fast fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef deliberate fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef verify fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc
    classDef gate fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
```

### Aletheia Verification States

The Generate-Verify-Revise loop and its four terminal states:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
stateDiagram-v2
    direction TB

    [*] --> Generate: Input query + context

    Generate --> Verify: Response candidate

    state Verify {
        direction LR
        [*] --> TraceExcluded: Verifier NEVER\nsees reasoning traces
        TraceExcluded --> SpecGaming: Check correct answer\nto wrong question?
        SpecGaming --> ScoreResult
    }

    Verify --> Revise: FAIL · cycle ≤ 3
    Revise --> Generate: Revised prompt

    Verify --> VERIFIED: PASS\nAll checks clear
    Verify --> UNVERIFIED: Cycle limit hit\nbut usable
    Verify --> UNPROVABLE: Cannot resolve\nparked with metadata
    Verify --> REFUSED: Safety violation\nor scope breach

    VERIFIED --> [*]: ✅ Delivered to user
    UNVERIFIED --> [*]: ⚠️ Delivered with caveat
    UNPROVABLE --> [*]: 🔒 Parked with dignity\nnot silently dropped
    REFUSED --> [*]: 🛑 Blocked by\nBasal Ganglia gate

    note right of Generate
        Max 3 GVR cycles
        (ADHD guard)
    end note

    note right of UNPROVABLE
        Full metadata preserved:
        query, attempts, failure mode
    end note
```

### Trace Lifecycle

The full journey of a memory trace — from storage through encoding, recall, Hebbian evolution, reconstruction, and eventual apoptosis. The reconsolidation boost creates a feedback loop that saves degraded traces from death when users actually retrieve their reconstructed episodes.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    STORE["twin_store()\nNew trace created"]:::input

    subgraph ENCODING["Encoding"]
        direction LR
        BGE["BGE Semantic\nEmbedding"]:::encode
        LSH["LSH Projection\n→ 2048-bit SDR"]:::encode
        SQLITE["Base SDR\nstored in SQLite\n🔒 pristine"]:::encode
        BGE --> LSH --> SQLITE
    end

    subgraph RECALL_PHASE["Recall · Lazy Decay"]
        direction TB
        QUERY["twin_recall()"]:::recall
        COMPUTE["strength = initial × e^(-λ·Δt)\n+ Σ(boosts)\n+ Σ(hebbian_boosts)"]:::recall
        THRESHOLD{"strength >\nepsilon?"}:::decision
        QUERY --> COMPUTE --> THRESHOLD
    end

    subgraph HEBBIAN_PHASE["Hebbian Evolution"]
        direction TB
        COACT["Co-Activation\nDetected"]:::hebbian
        SMASK["strengthen_mask\nshared bits ON"]:::hebbian
        WMASK["weaken_mask\ncompeting bits OFF"]:::hebbian
        EFFECTIVE["effective_sdr =\n(base | strengthen) & ~weaken"]:::hebbian
        VARIANT["Stored in USD\nVariant layer"]:::hebbian
        COACT --> SMASK
        COACT --> WMASK
        SMASK --> EFFECTIVE
        WMASK --> EFFECTIVE
        EFFECTIVE --> VARIANT
    end

    subgraph RECON["Episodic Reconstruction"]
        direction TB
        DEGRADE{"Below recon\nthreshold?"}:::decision
        REBUILD["Reconstruct from\nHebbian co-activations\nvia LIVRPS composition"]:::recon
        BOOST["Reconsolidation Boost\n🔑 fires ONLY on\nuser-facing retrieval"]:::recon
        DEGRADE -->|"yes"| REBUILD --> BOOST
    end

    subgraph DEATH["Apoptosis"]
        direction TB
        CLAMP["Apoptosis Clamp\nmax(apoptosis + 0.05, threshold)\nprevents race condition"]:::death
        DELETE["Physical DELETE\n+ VACUUM\nDB actually shrinks"]:::death
        CLAMP --> DELETE
    end

    HOMEO["Homeostatic Plasticity\nclamp density → 3%–5%"]:::homeo

    STORE --> ENCODING
    ENCODING --> RECALL_PHASE
    THRESHOLD -->|"yes · alive"| HEBBIAN_PHASE
    THRESHOLD -->|"no · dying"| RECON
    DEGRADE -->|"no · too far gone"| DEATH
    BOOST -->|"rescued"| RECALL_PHASE
    HEBBIAN_PHASE --> HOMEO
    HOMEO -->|"next retrieval"| RECALL_PHASE

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef encode fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef recall fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef decision fill:#4a3a1a,stroke:#f59e0b,color:#fde68a,font-weight:bold
    classDef hebbian fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef recon fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef death fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef homeo fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc
```

### Motor Cortex Decision Gate

Inhibition-default: every action must pass ALL five checks or it's blocked.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    ACTION["Proposed Action"]:::input

    DEFAULT["🛑 DEFAULT STATE: INHIBIT ALL\nEvery action blocked until all 5 pass"]:::inhibit

    ACTION --> DEFAULT

    subgraph CHECKS["Basal Ganglia · 5-Check Gate"]
        direction TB
        C1{"1. Anchor Check\nAligned with\ncore principles?"}:::check
        C2{"2. Consent Check\nUser authorized\nthis action?"}:::check
        C3{"3. Verification Check\nAletheia verified\nthe reasoning?"}:::check
        C4{"4. Reversibility Check\nCan this be\nundone?"}:::check
        C5{"5. Scope Check\nWithin declared\nboundaries?"}:::check

        C1 -->|"✅ pass"| C2
        C2 -->|"✅ pass"| C3
        C3 -->|"✅ pass"| C4
        C4 -->|"✅ pass"| C5
    end

    DEFAULT --> C1

    EXECUTE["✅ EXECUTE\nONE action per cycle"]:::pass
    C5 -->|"✅ all 5 pass"| EXECUTE

    BLOCK["🛑 BLOCKED\nAction inhibited"]:::fail
    C1 -->|"❌ fail"| BLOCK
    C2 -->|"❌ fail"| BLOCK
    C3 -->|"❌ fail"| BLOCK
    C4 -->|"❌ fail"| BLOCK
    C5 -->|"❌ fail"| BLOCK

    subgraph STRUCTURAL_LOCKS["🔒 Structurally Locked · Cannot Pass Gate"]
        direction LR
        FINANCIAL["Financial\nTransactions"]:::locked
        IRREVERSIBLE["Irreversible\nDeletions"]:::locked
    end

    RED["🔴 RED STATE\nHalts everything\nNo exceptions"]:::red

    RED -->|"overrides all"| BLOCK

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef inhibit fill:#5c1a1a,stroke:#ef4444,color:#fca5a5,font-weight:bold,stroke-width:3px
    classDef check fill:#1a1a2e,stroke:#f59e0b,color:#fde68a,font-weight:bold
    classDef pass fill:#1a4a1a,stroke:#22c55e,color:#bbf7d0,font-weight:bold,stroke-width:3px
    classDef fail fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef locked fill:#3a1a1a,stroke:#991b1b,color:#fca5a5,stroke-width:3px,stroke-dasharray: 5 5
    classDef red fill:#7f1d1d,stroke:#ef4444,color:#fff,font-weight:bold,stroke-width:3px
```

### Co-Evolution Spiral

How the Twin and the human transform each other through interaction:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    subgraph CYCLE["Co-Evolution · Twin ↔ Human"]
        direction TB

        H1["🧑 Human acts\nqueries, decisions, patterns"]:::human
        T1["🤖 Twin observes\nSDR encoding, trace storage"]:::twin
        T2["🤖 Twin learns\nHebbian evolution,\nskills tracking,\npattern detection"]:::twin
        T3["🤖 Twin reflects\nDMN inquiry,\ncrystallization,\nallostatic monitoring"]:::twin
        T4["🤖 Twin surfaces\npatterns, gaps,\nescalation warnings"]:::twin
        H2["🧑 Human integrates\nnew awareness,\nadjusted behavior"]:::human
        H3["🧑 Human transforms\nnew patterns emerge,\nold ones decay"]:::human

        H1 --> T1
        T1 --> T2
        T2 --> T3
        T3 --> T4
        T4 --> H2
        H2 --> H3
        H3 -->|"new patterns\nfeed back"| H1
    end

    subgraph SAFEGUARDS["Inquiry Safeguards"]
        direction LR
        APOPH["Apophenia Guard\ndon't hallucinate\npatterns"]:::guard
        SINC["Sincerity Gate\nonly surface what's\ngenuinely there"]:::guard
        RUPTURE["Rupture & Repair\nwhen surfacing\ncauses friction"]:::guard
    end

    T3 --> SAFEGUARDS

    INTELLIGENCE["The intelligence lives in\nthe relationship —\nnot in either party alone"]:::philosophy

    classDef human fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef twin fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc,font-weight:bold
    classDef guard fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef philosophy fill:#1a1a2e,stroke:#7c3aed,color:#c4b5fd,font-style:italic
```

## Key Design Decisions

**1-bit SDR bitvectors, not float embeddings.** Memory search uses 2048-bit Sparse Distributed Representations. Hamming distance via XOR + popcount. No cosine similarity, no float32 storage. The Rust hot path processes these at <2ms for recall.

**USD-Lite container format.** Every subsystem writes to a shared USD stage with 17 typed prim dataclasses. `.usda` text serialization with proven round-trip fidelity. LIVRPS composition with permanent-prim handling. Float tolerance via `math.isclose()`. SDR arrays packed as 512-char hex strings (not 6KB text arrays).

### LIVRPS Composition Precedence

Pixar's USD composition ordering adapted for brain state. Strongest opinion wins per attribute. Permanent prims (Amygdala reflexes) override everything.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    QUERY["Attribute Query\nWhich value wins?"]:::input

    subgraph LIVRPS["LIVRPS Precedence · Strongest Opinion Wins"]
        direction TB
        L["🔒 [L] Local Overrides\nDirect user corrections\n⬆ STRONGEST"]:::L
        I["[I] Inherits\nBase trait inheritance"]:::I
        V["[V] Variants\nHebbian dual-mask layer\nstrengthen_mask + weaken_mask"]:::V
        R["[R] References\nCross-trace links\nepistemic provenance"]:::R
        P["[P] Payloads\nRaw ingested data\ntrace content"]:::P
        S["[S] Specializes\nDomain-specific refinements\n⬇ WEAKEST"]:::S

        L --- I --- V --- R --- P --- S
    end

    PERM["⚡ Permanent Prims\nAmygdala reflexes\nOVERRIDE EVERYTHING\nincluding [L]"]:::perm

    QUERY --> LIVRPS
    PERM -->|"structural override"| L

    subgraph PROVENANCE["Typed Provenance · Every Layer"]
        direction LR
        P1["USER_DIRECT"]:::prov
        P2["EXTERNAL_REFERENCE"]:::prov
        P3["SYSTEM_INFERRED"]:::prov
        P4["HEBBIAN_DERIVED"]:::prov
        P5["INTAKE_CALIBRATED"]:::prov
    end

    subgraph RESOLUTION["Resolution Rules"]
        direction LR
        R1["Per-attribute\nnot per-prim"]:::rule
        R2["Conflict:\nhigher layer wins"]:::rule
        R3["Float tolerance:\nmath.isclose()"]:::rule
        R4["Merkle hash:\nbase traces only"]:::rule
    end

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef L fill:#7f1d1d,stroke:#ef4444,color:#fca5a5,font-weight:bold,stroke-width:3px
    classDef I fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef V fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef R fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef P fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef S fill:#1a1a2e,stroke:#6b7280,color:#9ca3af
    classDef perm fill:#4a1a4a,stroke:#d946ef,color:#f0abfc,font-weight:bold,stroke-width:3px
    classDef prov fill:#1a1a2e,stroke:#7c3aed,color:#c4b5fd
    classDef rule fill:#1a2a4a,stroke:#6366f1,color:#c7d2fe
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
