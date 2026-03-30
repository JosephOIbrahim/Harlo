# Cognitive Twin

Your AI forgets you every time. This fixes that.

The Cognitive Twin is a living model of how you think — not a chat log, not a search history, but a persistent layer of *you* that any AI can consult. It remembers your patterns, learns your instincts, verifies what it tells you, and evolves as you do.

> **Latest: Production-live.** Sprint 5 complete. Every MCP call evaluates cognitive state against real `.usda` files, delegates route by capability, observations accumulate, XGBoost predicts next state. 250 tests across 5 sprints. Kill switches for every component. The twin is watching, learning, predicting.

## The Problem

Every conversation with an AI starts from scratch. Close the window and everything you built together — your context, your shorthand, the way it was starting to *get* you — vanishes. The next session is a stranger again.

Current "memory" products store what you *said*. The Cognitive Twin stores how you *think*.

It sits between you and any AI, modeling your cognitive patterns: what surprises you, how you make connections, where your expertise runs deep, when you're running on fumes. The AI doesn't just remember your words — it understands your rhythm. And it gets sharper the longer you work together, not because the AI improved, but because your Twin learned more about you.

The intelligence lives in the relationship — not in either party alone.

## How It Works

```
                          COGNITIVE TWIN v8.0
                          ====================

  You ──► Actor (Claude via MCP, 8 tools)
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  ACTOR / OBSERVER ARCHITECTURE                                  │
  │                                                                │
  │  Actor (LLM) reasons ←── Coach Core projection ←── Observer      │
  │       │                                              │          │
  │       ▼                                              │          │
  │  ┌──────────────┐  ┌────────────────────────────────────┐       │
  │  │  HOT TIER    │  │  WARM TIER (L2)                    │       │
  │  │  (L1)        │  │                                    │       │
  │  │  FTS5 search │  │  SDR Hamming search (Rust/PyO3)   │       │
  │  │  Zero encode │  │  ONNX BGE + LSH → 2048-bit SDR   │       │
  │  │  <0.2ms store│  │  <2ms recall                      │       │
  │  └──────┬───────┘  └────────────────────────────────────┘       │
  │         │ Observer promotes (ONNX encode, background)    ▲       │
  │         └────────────────────────────────────────────────┘       │
  │                                                                │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  FEDERATED RECALL    │     │  ELENCHUS VERIFICATION   │     │
  │  │                      │     │  (GVR Loop, max 3)       │     │
  │  │  FTS5 + SDR Hamming  │     │                          │     │
  │  │  Score normalize     │     │  Trace-excluded verify   │     │
  │  │  Deduplicate + merge │     │  Spec-gaming detection   │     │
  │  └──────────────────────┘     │  v8: Actor-side deferral │     │
  │                               └──────────────────────────┘     │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  COMPOSITION ENGINE  │     │  MOTOR CORTEX            │     │
  │  │  (Left Hemisphere)   │     │                          │     │
  │  │  Merkle stages       │     │  Basal Ganglia           │     │
  │  │  LIVRPS resolution   │     │  (5-check gate,          │     │
  │  │  Structured          │     │   inhibit-default)       │     │
  │  │    Provenance        │     │  ONE action/cycle        │     │
  │  └──────────────────────┘     └──────────────────────────┘     │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  HEBBIAN ENGINE      │     │  INQUIRY ENGINE (DMN)    │     │
  │  │                      │     │                          │     │
  │  │  Dual-mask SDR       │     │  Pattern detection       │     │
  │  │    evolution         │     │  Apophenia guard         │     │
  │  │  Episodic context    │     │  Sincerity gate          │     │
  │  │    reconstruction    │     │  Rupture & repair        │     │
  │  │  Homeostatic [3%-5%] │     │  Crystallization         │     │
  │  └──────────────────────┘     └──────────────────────────┘     │
  │  ┌──────────────────────┐     ┌──────────────────────────┐     │
  │  │  USD-LITE CONTAINER  │     │  COGNITIVE PROFILE       │     │
  │  │  17 typed prims      │     │  Adaptive intake         │     │
  │  │  .usda serialization │     │  Trust Ledger [0,1]      │     │
  │  │  Hex SDR (512 chars) │     │  Skills observer         │     │
  │  └──────────────────────┘     └──────────────────────────┘     │
  │  ┌──────────────────────┐                                      │
  │  │  TEMPORAL COMPACTION  │                                      │
  │  │  Replay-then-archive │                                      │
  │  │  Decay commutation   │                                      │
  │  └──────────────────────┘                                      │
  └─────────────────────────────────────────────────────────────────┘
           │
           ▼
  Response (verified, contextual, personally calibrated)
```

The system is event-driven and socket-activated. It idles at 0 watts. No polling, no `sleep()`, no background threads. The daemon wakes on command, does its work, and exits. In v8.0, the Actor (Claude) reasons while the Observer (Twin) stores and projects — no local LLM required.

### Module Hierarchy

The v8.0 architecture as a dependency graph. The Actor (LLM) reasons via MCP tools. The Observer stores, encodes, and projects cognitive state. No LLM dependency in the Observer path.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed', 'secondaryColor': '#16213e', 'tertiaryColor': '#0f3460'}}}%%
graph TB
    ACTOR["Actor · Claude via MCP\n8 Tools · No local LLM"]:::entry
    OBSERVER["Observer · Background\n0W idle · No LLM deps"]:::entry

    subgraph HOT["Hot Tier · L1"]
        direction TB
        FTS5["FTS5 Full-Text Search\nzero-encoding\n< 0.2ms store"]:::hot
    end

    subgraph WARM["Warm Tier · L2"]
        direction TB
        ONNX["ONNX Encoder\nBGE + LSH → 2048-bit SDR"]:::warm
        RUST["Rust Hot Path · PyO3\nXOR + popcount kNN\n< 2ms recall"]:::warm
        DECAY["Lazy Decay\ncomputed on read"]:::warm
        ONNX --> RUST --> DECAY
    end

    subgraph COACH["Coach · System Prompt"]
        direction TB
        PROJ["Stage → XML Projection\ntrust, traces, claims"]:::coach
    end

    subgraph FED["Federated Recall"]
        direction TB
        MERGE["FTS5 + SDR Hamming\nnormalize + deduplicate"]:::fed
    end

    ACTOR -->|"twin_store"| HOT
    ACTOR -->|"query_past_experience"| FED
    ACTOR -->|"twin_coach"| COACH
    OBSERVER -->|"promote batch"| WARM
    FED --> HOT
    FED --> WARM
    COACH --> HOT

    subgraph BRAINSTEM["Brainstem · Lossless Translation"]
        direction TB
        ADAPT["Adapter Pairs\nnative ↔ USD prims"]:::brainstem
        ROUTE["Z-Score Surprise Router\nSystem 1 / System 2"]:::brainstem
        PROV["Structured Provenance\n5 source types"]:::brainstem
        ADAPT --> ROUTE --> PROV
    end

    subgraph LEFT["Composition Engine · Left Hemisphere"]
        direction TB
        MERKLE["Merkle Stages\nisolated hash trees"]:::left
        LIVRPS["LIVRPS Resolution\nstrongest opinion wins"]:::left
        AUDIT["Audit Trail"]:::left
        MERKLE --> LIVRPS --> AUDIT
    end

    subgraph ELENCHUS["Elenchus Verification"]
        direction TB
        GVR["GVR Loop\nmax 3 cycles"]:::verify
        SPEC["Spec-Gaming Detection"]:::verify
        TRACE_EX["Trace-Excluded Verify\nblinded verifier"]:::verify
        DEFER["v8 Deferral Queue\nObserver queues → Actor resolves"]:::verify
        GVR --> SPEC
        GVR --> TRACE_EX
        GVR --> DEFER
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
        PATTERN --> APOPH --> SINC
    end

    subgraph USD["USD-Lite Container"]
        direction TB
        PRIMS["17 Typed Prim Dataclasses"]:::usd
        USDA[".usda Serialization\nround-trip fidelity"]:::usd
        HEX["Hex SDR · 512 chars"]:::usd
        PRIMS --> USDA --> HEX
    end

    subgraph TRUST["Trust & Profile"]
        direction TB
        LEDGER["Trust Ledger\ncontinuous 0.0–1.0"]:::profile
        INTAKE["Adaptive Intake\nneuropsych-informed"]:::profile
        SKILLS["Skills Observer\nincremental"]:::profile
        RECAL["Recalibration\nre-triggerable"]:::profile
        LEDGER --> INTAKE
        INTAKE --> SKILLS
    end

    subgraph COMPACT["Temporal Compaction"]
        direction TB
        REPLAY["Replay-then-Archive\nchronological decay"]:::compact
    end

    %% Connections
    BRAINSTEM <-->|"USD prims"| USD
    BRAINSTEM --> LEFT
    BRAINSTEM --> ELENCHUS
    BRAINSTEM --> MOTOR
    BRAINSTEM --> HEBBIAN
    BRAINSTEM --> INQUIRY
    BRAINSTEM --> TRUST
    WARM --> COMPACT

    %% Styles
    classDef entry fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef hot fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,stroke-width:3px
    classDef warm fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef coach fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef fed fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef brainstem fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef left fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef verify fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc
    classDef motor fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef hebbian fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef inquiry fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef usd fill:#1a2a1a,stroke:#22c55e,color:#bbf7d0
    classDef profile fill:#3a1a4a,stroke:#d946ef,color:#f0abfc
    classDef compact fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
```

### Store & Recall Pipeline

How data flows through the v8.0 dual-tier system:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph LR
    USER["User Message"]:::input

    subgraph STORE_PATH["Store Path · Zero Latency"]
        direction TB
        MCP_S["twin_store\nMCP tool"]:::store
        HOT_W["Hot Tier · FTS5\nSQLite + triggers\n< 0.2ms"]:::store
        MCP_S --> HOT_W
    end

    subgraph PROMOTE["Observer Promotion"]
        direction TB
        PEND["get_pending()\nun-encoded traces"]:::promote
        ONNX_E["ONNX Encoder\nBGE + CLS pooling\n+ LSH → SDR"]:::promote
        WARM_W["Warm Tier\n256-byte SDR blob"]:::promote
        PEND --> ONNX_E --> WARM_W
    end

    subgraph RECALL_PATH["Recall Path · Federated"]
        direction TB
        QPE["query_past_experience"]:::recall
        HOT_R["FTS5 Search\nscore = 1/(1+rank)"]:::recall
        WARM_R["SDR Hamming Search\nscore = 1 - dist/2048"]:::recall
        MERGE["Normalize + Deduplicate\nhot wins on conflict\nrank by score"]:::recall
        QPE --> HOT_R
        QPE --> WARM_R
        HOT_R --> MERGE
        WARM_R --> MERGE
    end

    RESULT["Merged Ranked Results\ntrace_id, message, score, tier"]:::output

    USER --> STORE_PATH
    HOT_W -->|"background"| PROMOTE
    USER --> RECALL_PATH
    MERGE --> RESULT

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef output fill:#22c55e,stroke:#4ade80,color:#fff,font-weight:bold
    classDef store fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef promote fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef recall fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
```

### Elenchus Verification States

The Generate-Verify-Revise loop, its four terminal states, and the v8 Actor-side deferral model:

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

    state v8_Deferral {
        direction LR
        [*] --> ObserverQueue: Observer queues\nsemantic claims
        ObserverQueue --> CoachInject: Coach Core surfaces\npending claims
        CoachInject --> ActorResolve: Actor calls\nresolve_verifications
    }

    VERIFIED --> [*]: Delivered to user
    UNVERIFIED --> [*]: Delivered with caveat
    UNPROVABLE --> v8_Deferral: Queued for Actor
    REFUSED --> [*]: Blocked by\nBasal Ganglia gate

    note right of Generate
        Max 3 GVR cycles
        (ADHD guard)
    end note

    note right of v8_Deferral
        v8: No local LLM needed.
        Observer queues claims,
        Actor resolves when connected.
    end note
```

### Trace Lifecycle

The full journey of a memory trace — from hot storage through encoding, promotion, recall, Hebbian evolution, compaction, and eventual apoptosis:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    STORE["twin_store()\nNew trace created"]:::input

    subgraph HOT_STORE["Hot Tier · Instant"]
        direction LR
        FTS["FTS5 Index\nzero-encoding"]:::hot
        PENDING["encoded=FALSE\nawaiting promotion"]:::hot
        FTS --> PENDING
    end

    subgraph PROMOTION["Observer Promotes"]
        direction LR
        ONNX_P["ONNX Encode\nBGE + LSH → SDR"]:::promote
        WARM_S["Warm Tier\n256-byte SDR blob\nencoded=TRUE"]:::promote
        ONNX_P --> WARM_S
    end

    subgraph RECALL_PHASE["Recall · Lazy Decay"]
        direction TB
        QUERY["query_past_experience()"]:::recall
        COMPUTE["strength = initial * e^(-lambda*dt)\n+ sum(boosts)\n+ sum(hebbian_boosts)"]:::recall
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
        BOOST["Reconsolidation Boost\nfires ONLY on\nuser-facing retrieval"]:::recon
        DEGRADE -->|"yes"| REBUILD --> BOOST
    end

    subgraph COMPACTION["Temporal Compaction"]
        direction TB
        REPLAY["Replay variants\nwith decay at t_now"]:::compact
        ARCHIVE["Archive to\n.usda.archive/"]:::compact
        REPLAY --> ARCHIVE
    end

    subgraph DEATH["Apoptosis"]
        direction TB
        CLAMP["Apoptosis Clamp\nmax(apoptosis + 0.05, threshold)"]:::death
        DELETE["Physical DELETE\n+ VACUUM\nDB actually shrinks"]:::death
        CLAMP --> DELETE
    end

    HOMEO["Homeostatic Plasticity\nclamp density to 3%-5%"]:::homeo

    STORE --> HOT_STORE
    PENDING -->|"Observer"| PROMOTION
    PROMOTION --> RECALL_PHASE
    HOT_STORE -->|"FTS5 search"| RECALL_PHASE
    THRESHOLD -->|"yes · alive"| HEBBIAN_PHASE
    THRESHOLD -->|"no · dying"| RECON
    DEGRADE -->|"no · too far gone"| DEATH
    BOOST -->|"rescued"| RECALL_PHASE
    HEBBIAN_PHASE --> HOMEO
    HOMEO -->|"next retrieval"| RECALL_PHASE
    VARIANT -->|"idle compaction"| COMPACTION

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef hot fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,stroke-width:3px
    classDef promote fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef recall fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef decision fill:#4a3a1a,stroke:#f59e0b,color:#fde68a,font-weight:bold
    classDef hebbian fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef recon fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef compact fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef death fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef homeo fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc
```

### Motor Cortex Decision Gate

Inhibition-default: every action must pass ALL five checks or it's blocked.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    ACTION["Proposed Action"]:::input

    DEFAULT["DEFAULT STATE: INHIBIT ALL\nEvery action blocked until all 5 pass"]:::inhibit

    ACTION --> DEFAULT

    subgraph CHECKS["Basal Ganglia · 5-Check Gate"]
        direction TB
        C1{"1. Anchor Check\nAligned with\ncore principles?"}:::check
        C2{"2. Consent Check\nUser authorized\nthis action?"}:::check
        C3{"3. Verification Check\nElenchus verified\nthe reasoning?"}:::check
        C4{"4. Reversibility Check\nCan this be\nundone?"}:::check
        C5{"5. Scope Check\nWithin declared\nboundaries?"}:::check

        C1 -->|"pass"| C2
        C2 -->|"pass"| C3
        C3 -->|"pass"| C4
        C4 -->|"pass"| C5
    end

    DEFAULT --> C1

    EXECUTE["EXECUTE\nONE action per cycle"]:::pass
    C5 -->|"all 5 pass"| EXECUTE

    BLOCK["BLOCKED\nAction inhibited"]:::fail
    C1 -->|"fail"| BLOCK
    C2 -->|"fail"| BLOCK
    C3 -->|"fail"| BLOCK
    C4 -->|"fail"| BLOCK
    C5 -->|"fail"| BLOCK

    subgraph STRUCTURAL_LOCKS["Structurally Locked · Cannot Pass Gate"]
        direction LR
        FINANCIAL["Financial\nTransactions"]:::locked
        IRREVERSIBLE["Irreversible\nDeletions"]:::locked
    end

    RED["RED STATE\nHalts everything\nNo exceptions"]:::red

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

        H1["Human acts\nqueries, decisions, patterns"]:::human
        T1["Twin observes\nHot Tier store, SDR encoding"]:::twin
        T2["Twin learns\nHebbian evolution,\nskills tracking,\npattern detection"]:::twin
        T3["Twin reflects\nDMN inquiry,\ncrystallization,\nallostatic monitoring"]:::twin
        T4["Twin surfaces\nCoach Core projection,\ntrust-gated coaching"]:::twin
        H2["Human integrates\nnew awareness,\nadjusted behavior"]:::human
        H3["Human transforms\nnew patterns emerge,\nold ones decay"]:::human

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

### Cognitive State Machine (Sprint 1)

The cognitive state simulation pipeline — from authored observations through the DAG evaluator to validated trajectories and XGBoost prediction:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    subgraph GEN["Trajectory Generator · Profile-Driven Markov"]
        direction TB
        PROFILES["7 Session Profiles\nnormal 40% · deep_work 15%\nstruggling 15% · recovery 10%\ninjection 10% · crisis 5% · mobile 5%"]:::gen
        AUTHOR["Author Observations\nvelocity · coherence · frustration\ntasks · burst · injection"]:::gen
        PROFILES --> AUTHOR
    end

    subgraph STAGE["MockUsdStage · Dict Storage"]
        direction TB
        STORE["(prim_path, exchange_index) → value\nread_previous(path, 0) = baseline\nNEVER None · NEVER KeyError"]:::stage
    end

    subgraph DAG["MockCogExec · networkx DiGraph"]
        direction TB
        TOPO["Topological Sort\nburst → energy → momentum → burnout → allostasis"]:::dag

        subgraph COMPUTE["Pure Computation Functions"]
            direction LR
            BURST["compute_burst\nNONE→DETECTED→\nPROTECTED→WINDING→\nEXIT_PREP→NONE"]:::compute
            ENERGY["compute_energy\nadrenaline masking\nRED degradation\nexercise recovery"]:::compute
            MOMENTUM["compute_momentum\nCRASHED→COLD_START→\nBUILDING→ROLLING→PEAK"]:::compute
            BURNOUT["compute_burnout\nGREEN→YELLOW→\nORANGE→RED\nexogenous override"]:::compute
            ALLO["compute_allostasis\n6-weight composite\ntrend detection"]:::compute
        end

        subgraph INDEPENDENT["Independent Computations"]
            direction LR
            INJECT["compute_injection_gain\nanchor = 1.0 ALWAYS\n4 profile curves"]:::compute
            CONTEXT["compute_context_budget\nhysteresis 3.8x / 4.2x"]:::compute
        end

        TOPO --> COMPUTE
        TOPO --> INDEPENDENT
    end

    subgraph POST["Post-DAG Invariant Enforcement"]
        direction LR
        INV11["INV-11: RED → CRASHED"]:::enforce
        INV15["INV-15: RED kills burst"]:::enforce
    end

    subgraph VALIDATE["Validator · 26 Invariants"]
        direction TB
        V26["INV-01 to INV-26\nstate ranges · transitions\nanchors · temporal monotonicity\nadrenaline masking · RED rules"]:::validate
    end

    subgraph OUTPUT["Output"]
        direction LR
        JSONL["10,000 JSONL trajectories\n278,577 exchanges\n0 violations"]:::output
        XGBOOST["XGBoost Predictor\n100% per-field accuracy\n111 features · 4 targets"]:::output
        BRIDGE["Bridge Integration\n50-exchange end-to-end\nDelegate + Buffer + Predictor"]:::output
    end

    AUTHOR --> STAGE
    STAGE -->|"read_previous(t-1)"| DAG
    DAG --> POST
    POST -->|"author(t)"| STAGE
    POST --> VALIDATE
    VALIDATE --> OUTPUT

    classDef gen fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef stage fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,stroke-width:3px
    classDef dag fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef compute fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef enforce fill:#5c1a1a,stroke:#ef4444,color:#fca5a5,font-weight:bold
    classDef validate fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef output fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,font-weight:bold
```

### State Machine Transitions

The five cognitive state machines and their transition rules:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
stateDiagram-v2
    direction LR

    state Momentum {
        direction LR
        [*] --> COLD_START
        CRASHED --> COLD_START: always
        COLD_START --> BUILDING: tasks ≥ threshold
        BUILDING --> ROLLING: coherence + velocity
        ROLLING --> PEAK: exchanges + burst
        PEAK --> CRASHED: burnout ≥ ORANGE
    }

    state Burnout {
        direction LR
        [*] --> GREEN
        GREEN --> YELLOW: frustration or duration
        YELLOW --> ORANGE: sustained frustration
        ORANGE --> RED: extreme frustration
        note right of RED: ANY → RED via exogenous override
    }

    state Energy {
        direction LR
        [*] --> MEDIUM
        HIGH --> MEDIUM: natural decay
        MEDIUM --> LOW: session length
        LOW --> DEPLETED: continued work
        note right of DEPLETED: Burst suspends decay\nDebt applies on exit
    }

    state Burst {
        direction LR
        [*] --> NONE_B
        NONE_B --> DETECTED: velocity + coherence
        DETECTED --> PROTECTED: sustained
        PROTECTED --> WINDING: exchange threshold
        WINDING --> EXIT_PREP: exit threshold
        EXIT_PREP --> NONE_B: next exchange
    }
```

### OpenExec Build Status (Sprint 2)

The USD 26.03 build pipeline and current status:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph LR
    subgraph BUILD["USD 26.03 Build · Windows"]
        direction TB
        MSVC["MSVC 19.44\nVS2022 Build Tools"]:::ready
        CMAKE["CMake 4.2.1"]:::ready
        PY312["Python 3.12.10"]:::ready
        FLAGS["--no-imaging\n--no-usdview\n-DPXR_BUILD_EXEC=ON"]:::ready
    end

    subgraph RESULT["Build Output"]
        direction TB
        CORE["USD Core\npxr.Usd, Sdf, Tf\n31 plugins"]:::pass
        CPP["Exec C++ Libraries\nusd_exec.dll\nusd_execGeom.dll\nusd_execIr.dll\nusd_execUsd.dll"]:::pass
        SCHEMA["usdGenSchema\navailable"]:::pass
        PYTHON["Exec Python Bindings\nZERO wrap files\nin v26.03 source"]:::fail
    end

    subgraph STATUS["Sprint 2 Status"]
        direction TB
        MOCK["MockCogExec\ncontinues to serve\n84 tests passing"]:::active
        FUTURE["Awaiting Pixar\nPython bindings\nin future USD release"]:::waiting
    end

    BUILD --> RESULT
    PYTHON -->|"CIRCUIT BREAKER"| STATUS

    classDef ready fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef pass fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,font-weight:bold
    classDef fail fill:#5c1a1a,stroke:#ef4444,color:#fca5a5,font-weight:bold,stroke-width:3px
    classDef active fill:#0f3460,stroke:#3b82f6,color:#93c5fd,font-weight:bold
    classDef waiting fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
```

### Hydra Delegate Routing (Sprint 3)

The Hydra pattern: DAG outputs capability requirements, registry selects the delegate. The DAG never names a specific LLM.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    MCP["MCP Tool Call\ntwin_coach, twin_store, ..."]:::input

    subgraph ENGINE["CognitiveEngine"]
        direction TB
        DAG["DAG Evaluation\nburst → energy → momentum\n→ burnout → allostasis"]:::dag
        ROUTE["compute_routing\nOutputs: requirements\nNOT delegate names"]:::route

        subgraph SAFETY["Safety Overrides"]
            direction LR
            RED["RED → force restorer\nconsent ignored"]:::red
            ORANGE["ORANGE + no consent\n→ force restorer"]:::orange
            CONSENT["OOB Consent Token\nHMAC-signed · TTL · revocable\napplication-layer only"]:::consent
        end

        DAG --> ROUTE
        ROUTE --> SAFETY
    end

    subgraph REGISTRY["Delegate Registry · Capability Matching"]
        direction TB
        MATCH["Filter: requires_coding\nFilter: supported_tasks\nFilter: latency_class\nFilter: context_budget"]:::registry

        subgraph DELEGATES["Registered Delegates"]
            direction LR
            CLAUDE["HdClaude\nreasoning · coaching\narchitecture · analysis\ninteractive · 200K ctx"]:::claude
            CODE["HdClaudeCode\nimplementation · debugging\ncode_generation · testing\nbatch · 200K ctx"]:::code
            FUTURE["Future Delegate\nimplement interface\nregister · done"]:::future
        end

        MATCH --> DELEGATES
    end

    subgraph SUBLAYERS["Per-Delegate Sublayers"]
        direction LR
        SUB_C["claude.usda\ninteractive opinions\nSTRONGEST"]:::sub
        SUB_CC["claude_code.usda\nbatch opinions"]:::sub
    end

    MCP --> ENGINE
    SAFETY --> REGISTRY
    DELEGATES --> SUBLAYERS

    OBSERVE["Observation Buffer\nanchor 20% · organic 80%\nSQLite priority queue"]:::observe
    PREDICT["XGBoost Predictor\n3-step window\n111 features → 4 targets"]:::predict

    SUBLAYERS --> OBSERVE
    SUBLAYERS --> PREDICT

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef dag fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef route fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef red fill:#7f1d1d,stroke:#ef4444,color:#fff,font-weight:bold
    classDef orange fill:#5c1a1a,stroke:#ef4444,color:#fca5a5
    classDef consent fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef registry fill:#2e1a4a,stroke:#a78bfa,color:#ddd6fe
    classDef claude fill:#0f3460,stroke:#3b82f6,color:#93c5fd,font-weight:bold
    classDef code fill:#1a3a4a,stroke:#06b6d4,color:#a5f3fc,font-weight:bold
    classDef future fill:#1a1a2e,stroke:#6b7280,color:#9ca3af,stroke-dasharray: 5 5
    classDef sub fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0
    classDef observe fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef predict fill:#3a1a4a,stroke:#d946ef,color:#f0abfc
```

### Production Data Flow (Sprint 5)

The live pipeline from Claude Desktop through the cognitive engine to `.usda` on disk:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph LR
    CLAUDE["Claude Desktop\nvia MCP stdio"]:::input

    subgraph MCP_SERVER["MCP Server · 8 Tools"]
        direction TB
        TOOLS["twin_coach · twin_store\ntwin_recall · twin_patterns\ntwin_session_status\nquery_past_experience\nresolve_verifications\ntrigger_recalibration"]:::tools
    end

    subgraph COGNITIVE_ENGINE["CognitiveEngine · Singleton"]
        direction TB
        AUTHOR["1. Author\nexchange data"]:::step
        EVAL["2. Evaluate\nDAG"]:::step
        ROUTING["3. Route\nby capability"]:::step
        DELEGATE["4. Delegate\nsync/execute/commit"]:::step
        OBS["5. Observe\nemit to buffer"]:::step
        PRED["6. Predict\nXGBoost forecast"]:::step
        SAVE["7. Save\n.usda to disk"]:::step
        AUTHOR --> EVAL --> ROUTING --> DELEGATE --> OBS --> PRED --> SAVE
    end

    subgraph PERSISTENCE["On Disk · Git-Trackable"]
        direction TB
        USDA["cognitive_twin.usda\nReal USD · Time-sampled\nHuman-readable"]:::usda
        SUBS["delegates/\nclaude.usda\nclaude_code.usda"]:::usda
        OBSDB["observations.db\nSQLite buffer\nanchor + organic"]:::db
    end

    RESPONSE["Enriched Response\ncognitive context\ndelegate ID · expert\nprediction"]:::output

    CLAUDE --> MCP_SERVER
    MCP_SERVER --> COGNITIVE_ENGINE
    COGNITIVE_ENGINE --> PERSISTENCE
    COGNITIVE_ENGINE --> RESPONSE
    RESPONSE --> CLAUDE

    classDef input fill:#7c3aed,stroke:#a78bfa,color:#fff,font-weight:bold
    classDef tools fill:#0f3460,stroke:#3b82f6,color:#93c5fd
    classDef step fill:#1e3a5f,stroke:#60a5fa,color:#bfdbfe
    classDef usda fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,font-weight:bold,stroke-width:3px
    classDef db fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef output fill:#22c55e,stroke:#4ade80,color:#fff,font-weight:bold
```

### Graceful Degradation (Sprint 5)

Every component fails independently. The MCP server never crashes.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1a1a2e', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#7c3aed', 'lineColor': '#7c3aed'}}}%%
graph TB
    ENGINE["CognitiveEngine"]:::engine

    subgraph COMPONENTS["Independent Failure Isolation"]
        direction TB
        STAGE_OK{"Stage\ninit?"}:::check
        DAG_OK{"DAG\neval?"}:::check
        DELEGATE_OK{"Delegate\ncycle?"}:::check
        OBS_OK{"Observation\nwrite?"}:::check
        PRED_OK{"Prediction\nrun?"}:::check
        SAVE_OK{"Stage\nsave?"}:::check
    end

    subgraph FALLBACKS["Fallback Behaviors"]
        direction TB
        F1["MockUsdStage\n(dict fallback)"]:::fallback
        F2["Default computed\nvalues"]:::fallback
        F3["Empty context\nreturned"]:::fallback
        F4["Memory queue\n(max 100)"]:::fallback
        F5["Prediction\nskipped"]:::fallback
        F6["Queued for\nnext exchange"]:::fallback
    end

    MCP["MCP Server\nNEVER CRASHES"]:::safe

    ENGINE --> STAGE_OK
    STAGE_OK -->|"fail"| F1
    STAGE_OK -->|"ok"| DAG_OK
    DAG_OK -->|"fail"| F2
    DAG_OK -->|"ok"| DELEGATE_OK
    DELEGATE_OK -->|"fail"| F3
    DELEGATE_OK -->|"ok"| OBS_OK
    OBS_OK -->|"fail"| F4
    OBS_OK -->|"ok"| PRED_OK
    PRED_OK -->|"fail"| F5
    PRED_OK -->|"ok"| SAVE_OK
    SAVE_OK -->|"fail"| F6

    F1 --> MCP
    F2 --> MCP
    F3 --> MCP
    F4 --> MCP
    F5 --> MCP
    F6 --> MCP
    SAVE_OK -->|"ok"| MCP

    classDef engine fill:#0f3460,stroke:#3b82f6,color:#93c5fd,font-weight:bold
    classDef check fill:#1a1a2e,stroke:#f59e0b,color:#fde68a,font-weight:bold
    classDef fallback fill:#4a3a1a,stroke:#f59e0b,color:#fde68a
    classDef safe fill:#1a4a3a,stroke:#22c55e,color:#bbf7d0,font-weight:bold,stroke-width:3px
```

## Key Design Decisions

**Actor/Observer split (v8.0).** The Actor (Claude) reasons. The Observer (Twin) stores and projects. The MCP server requires no `ANTHROPIC_API_KEY` — it is a pure data layer. The Observer runs background SDR encoding and promotion without any LLM dependency. The Coach projects cognitive state as a system prompt for the Actor.

**Hot/Warm tiered memory (v8.0).** Traces are stored instantly to the Hot Tier via FTS5 (zero-encoding, <0.2ms p99). The Observer asynchronously promotes them to the Warm Tier via ONNX SDR encoding. Federated recall (`query_past_experience`) searches both tiers simultaneously, normalizes scores, deduplicates, and returns merged ranked results.

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
        L["[L] Local Overrides\nDirect user corrections\nSTRONGEST"]:::L
        I["[I] Inherits\nBase trait inheritance"]:::I
        V["[V] Variants\nHebbian dual-mask layer\nstrengthen_mask + weaken_mask"]:::V
        R["[R] References\nCross-trace links\nepistemic provenance"]:::R
        P["[P] Payloads\nRaw ingested data\ntrace content"]:::P
        S["[S] Specializes\nDomain-specific refinements\nWEAKEST"]:::S

        L --- I --- V --- R --- P --- S
    end

    PERM["Permanent Prims\nAmygdala reflexes\nOVERRIDE EVERYTHING\nincluding L"]:::perm

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

**Trust Ledger (v8.0).** A continuous [0.0, 1.0] trust score gates Observer behavior. Tiers: New (0.0–0.3, passive store only), Familiar (0.3–0.7, context/pattern surfacing), Trusted (0.7–1.0, proactive coaching/pushback). The Basal Ganglia evaluates the float directly. `trigger_cognitive_recalibration` resets trust + profile for major life changes.

**Lazy decay, not polling.** Trace strength is computed on retrieval: `strength = initial * e^(-lambda * dt) + sum(boosts) + sum(hebbian_boosts)`. No background jobs. Traces below epsilon are physically deleted (apoptosis) with `VACUUM` — the database actually shrinks.

**Temporal compaction (v8.0).** Deep-idle process replays variant stacks chronologically with exponential decay, writes resolved baselines, and archives originals. Critical invariant: `flatten(decay(variants)) == decay(flatten(variants))` — verified by tests.

**Elenchus verification pipeline.** Every LLM response runs through Generate-Verify-Revise. Max 3 cycles (ADHD guard). The verifier never sees reasoning traces (structural constraint). Spec-gaming detection catches correct answers to wrong questions. Unresolvable outputs are parked as UNPROVABLE with full metadata. In v8.0, the Observer queues semantic claims and the Actor resolves them via `resolve_verifications` — no local LLM required.

**Inhibition-default motor cortex.** The Basal Ganglia gate defaults to INHIBIT ALL. Every action requires all five checks (anchor, consent, verification, reversibility, scope). Financial transactions and irreversible deletions are structurally locked. RED state halts everything.

**Structured provenance.** Every composition layer carries a typed Provenance dataclass (source_type, origin_timestamp, event_hash, session_id). Five source types: USER_DIRECT, EXTERNAL_REFERENCE, SYSTEM_INFERRED, HEBBIAN_DERIVED, INTAKE_CALIBRATED. Legacy layers receive SYSTEM_INFERRED during migration.

**Elenchus training data pipeline.** Every verification event appends a JSONL row with the full cognitive profile feature vector (not just a hash). O(1) amortized log rotation at 10,000 rows. No reasoning traces (Rule 11). Ready for LoRA fine-tuning of a personalized verification model.

## Quick Start

```bash
git clone <repo-url> && cd cognitive-twin

# Python environment
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .
pip install onnxruntime transformers

# Build Rust hot path (optional — system falls back to Python encoding)
pip install maturin
maturin develop -r

# v8: No ANTHROPIC_API_KEY needed for the MCP server.
# The Actor (Claude) provides reasoning. The Twin stores and projects.
```

## Project Structure

```
src/                               Cognitive State Machine + Production Engine
├── schemas.py                     Pydantic IntEnum ordinals + CognitiveObservation model
├── cognitive_engine.py            Production singleton: DAG → route → delegate → observe → predict
├── cognitive_stage.py             Real pxr.Usd.Stage wrapper (Sprint 4)
├── mock_usd_stage.py              Dict-based fallback stage (Sprint 1)
├── stage_factory.py               Backend toggle: real USD or dict mock
├── mock_cogexec.py                networkx DAG evaluator — topological computation sort
├── usd_bootstrap.py               USD 26.03 sys.path + DLL directory setup
├── engine_config.py               Kill switches: ENGINE_ENABLED, USE_REAL_USD, etc.
├── delegate_base.py               HdCognitiveDelegate ABC (Hydra pattern)
├── delegate_registry.py           Capability-matching delegate selection
├── delegate_claude.py             Interactive reasoning delegate
├── delegate_claude_code.py        Implementation/code delegate
├── consent.py                     OOB consent tokens (HMAC-signed, TTL, revocable)
├── computations/                  Pure functions (no internal counters)
│   ├── compute_momentum.py        CRASHED→COLD_START→BUILDING→ROLLING→PEAK
│   ├── compute_burnout.py         GREEN→YELLOW→ORANGE→RED + exogenous override
│   ├── compute_energy.py          Adrenaline masking during burst, debt on exit
│   ├── compute_injection_gain.py  Anchor gain = 1.0 ALWAYS
│   ├── compute_context_budget.py  Hysteresis: promote >4.2x, demote <3.8x
│   ├── compute_burst.py           5-phase hyperfocus lifecycle
│   ├── compute_allostasis.py      6-weight composite load + trend detection
│   └── compute_routing.py         Capability requirements (NOT delegate names)
├── trajectory_generator.py        Profile-Driven Markov Biasing — 10K sessions
├── validator.py                   26 invariants (INV-01 to INV-26, RED exception)
├── train_predictor.py             XGBoost MultiOutputRegressor — ordinal encoding
├── predict.py                     Inference: 3-step window → next state prediction
├── bridge.py                      Exchange loop coordinator (simulation)
└── observation_buffer.py          SQLite priority queue — anchor 20% / organic 80%

python/cognitive_twin/             Core Twin: MCP server + biologically-architected memory
├── mcp_server.py                  8 MCP tools over stdio transport
├── elenchus/                      Verification engine — GVR loop, spec-gaming, trace exclusion
├── elenchus_v8/                   v8 deferred verification — pending queue, Actor-side resolution
├── brainstem/                     Lossless translation — adapters, routing, generation pipeline
├── cli/                           Click CLI — human + JSON output
├── coach/                         v8 Coach Core — stage → system prompt projection
├── compaction/                    v8 temporal compaction — replay-then-archive
├── composition/                   Left hemisphere — Merkle stages, LIVRPS resolution
├── daemon/                        Socket-activated daemon — router, config, lifecycle
├── encoder/                       Triple-path encoding — BGE+LSH, Rust, ONNX
├── federated_recall.py            v8 federated query — FTS5 + SDR Hamming merged search
├── hebbian/                       Neuroplasticity — dual-mask SDR evolution, reconstruction
├── hot_store/                     v8 Hot Tier (L1) — SQLite + FTS5, zero-encoding
├── inquiry/                       Default Mode Network — pattern surfacing, co-evolution
├── intake/                        Cognitive profile — adaptive questionnaire
├── modulation/                    Allostatic load, gain, barrier, pattern detection
├── motor/                         Motor cortex — Basal Ganglia gate, executor
├── observer/                      v8 Observer — background Hot→Warm promotion
├── provider/                      LLM abstraction — Claude and OpenAI adapters
├── session/                       Session lifecycle — SQLite-backed, history
├── skills/                        Competence tracking — incremental observer
├── trust/                         v8 Trust Ledger — continuous [0,1] score
├── usd_lite/                      USD container — 17 prim dataclasses, .usda serialization
└── migrate_v7.py                  v6 → v7 migration

crates/hippocampus/                Rust hot path — SDR encode, XOR search, lazy decay, apoptosis
config/                            Barrier schema, verification depth, default profile
data/
├── stages/                        Real .usda files — your cognitive state on disk
│   ├── cognitive_twin.usda        Root stage with time-sampled observations
│   └── delegates/                 Per-delegate sublayers (claude.usda, claude_code.usda)
├── observations.db                Organic observation buffer (SQLite)
└── twin.db                        Core Twin database (traces, sessions, trust)
models/                            ONNX models + cognitive_predictor_v1.joblib (XGBoost)
scripts/                           first_session.py, health_check.py, daemon, USD build
docs/                              PRODUCTION.md, ARCHITECTURE.md, OPENEXEC_BUILD.md
tests/                             35 test modules across 5 sprints + core
```

## Testing

**250 sprint tests** (5 sprints) + **890 core Twin tests** + **41 Rust tests**. All passing.

```bash
# All sprint tests (Python 3.12 for real USD)
.venv312/Scripts/python -m pytest tests/test_sprint1/ tests/test_sprint3/ \
    tests/test_sprint4/ tests/test_sprint5/ -v                    # 250 tests

# Individual sprints
python -m pytest tests/test_sprint1/ -v                           # S1: State machine (84)
python -m pytest tests/test_sprint3/ -v                           # S3: Hydra delegates (85)
.venv312/Scripts/python -m pytest tests/test_sprint4/ -v          # S4: Real USD (59)
python -m pytest tests/test_sprint5/ -v                           # S5: Production (22)

# Core Twin
python -m pytest tests/ -v --ignore=tests/test_sprint* \
    --ignore=tests/test_encoder --ignore=tests/test_daemon        # 890 tests

# Rust + health
cargo test -p hippocampus                                         # 41 tests
python scripts/health_check.py                                    # Production status
```

| Sprint | Tests | Coverage |
|--------|-------|----------|
| **S1** | 84 | Schemas, DAG, 7 computations, 26 invariants, 10K trajectories, XGBoost |
| **S3** | 85 | Delegate ABC, registry, routing, consent tokens, sublayers, 20-exchange e2e |
| **S4** | 59 | CognitiveStage (pxr.Usd), parity (mock vs real USD), .usda on disk |
| **S5** | 22 | Engine wiring, graceful degradation, 7 MCP tools hardened, crash recovery |
| **Core** | 890 | Memory tiers, SDR encoding, Elenchus, Hebbian, composition, motor, inquiry |

## Research Alignment

| Research Concept | Implementation | Status |
|---|---|---|
| SSGM temporal decay | Lazy decay with Hebbian boost integration | Extended |
| SSGM pre-consolidation validation | Elenchus trace exclusion (blinded) | Already ahead |
| SSGM provenance | Structured 5-type Provenance dataclass | **New in v7** |
| SSGM fragment reconstruction | Episodic reconstruction via Hebbian + LIVRPS | **New in v7** |
| Titans test-time memorization | Hebbian dual-mask SDR evolution | **New in v7** |
| Titans forgetting gate | Apoptosis (more aggressive, with clamp) | Already ahead |
| Mnemis entropy gating | Z-score surprise metric + dual-process routing | **New in v7** |
| HiMem reconsolidation | Brain-wide LIVRPS + reconsolidation boost | Extended |
| LoCoMo-Plus Level-2 memory | Skills observer + competence tracking | **New in v7** |
| Analog I sovereign refusal | Basal Ganglia inhibition-default gate | Already ahead |
| (No equivalent in literature) | Cognitive Profile intake system | **Original** |
| (No equivalent in literature) | Hot/Warm tiered memory with federated recall | **New in v8** |
| (No equivalent in literature) | Actor/Observer disaggregation (zero-LLM Observer) | **New in v8** |
| (No equivalent in literature) | Coach Core system prompt projection from cognitive state | **New in v8** |
| (No equivalent in literature) | Replay-then-archive temporal compaction | **New in v8** |
| (No equivalent in literature) | Cognitive state DAG simulation (networkx, pure functions) | **Sprint 1** |
| (No equivalent in literature) | Profile-Driven Markov Biasing for synthetic trajectories | **Sprint 1** |
| (No equivalent in literature) | XGBoost cognitive state predictor (ordinal + one-hot encoding) | **Sprint 1** |
| OpenUSD 26 OpenExec | C++ libs built, Python bindings pending from Pixar | **Sprint 2 (blocked)** |
| (No equivalent in literature) | Hydra Cognitive Delegate pattern (capability-requirement routing) | **Sprint 3** |
| (No equivalent in literature) | OOB consent tokens (HMAC-signed, TTL, revocable, app-layer only) | **Sprint 3** |
| (No equivalent in literature) | Sublayer-per-delegate concurrency (LIVRPS composition) | **Sprint 3** |
| (No equivalent in literature) | Real `pxr.Usd.Stage` with time-sampled cognitive state | **Sprint 4** |
| (No equivalent in literature) | Production graceful degradation (independent failure isolation) | **Sprint 5** |

## MCP Quick Reference

The Cognitive Twin exposes 8 tools via [Model Context Protocol](https://modelcontextprotocol.io). Works with Claude Desktop, Claude Code, and any MCP-compatible client. No `ANTHROPIC_API_KEY` required — the Actor (Claude) provides reasoning, the Twin stores and projects.

### `twin_store` — Store a memory trace (Hot Tier)

```
twin_store(message, domain?, tags?)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `message` | string | yes | `"Resolved Python 3.12 path issue by installing mcp into PATH Python"` |
| `domain` | string | no | `"technical"`, `"debugging"`, `"architecture"`, `"decision"` |
| `tags` | string[] | no | `["mcp", "python-path", "resolved"]` |

Zero-encoding hot path. Writes to FTS5-indexed Hot Tier in <0.2ms. Returns `{status: "stored", trace_id, tier: "hot", encoded: false}`. Observer promotes to Warm Tier asynchronously.

### `query_past_experience` — Federated recall (Hot + Warm)

```
query_past_experience(query, limit?)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `query` | string | yes | `"Python import issues"` |
| `limit` | integer | no | `10` (default) |

Searches both Hot Tier (FTS5 plaintext) and Warm Tier (SDR Hamming distance) simultaneously. Returns merged, deduplicated, ranked results with tier labels and normalized scores.

### `twin_recall` — Warm-tier semantic search

```
twin_recall(query, depth?)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `query` | string | yes | `"Python import issues"` |
| `depth` | `"normal"` \| `"deep"` | no | `"normal"` (top 5) or `"deep"` (top 15) |

Warm-tier SDR Hamming distance search. Returns matching traces ranked by distance with strength scores and confidence. For federated search across both tiers, use `query_past_experience`.

### `twin_coach` — Coaching context (system prompt projection)

```
twin_coach(session_id?)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `session_id` | string | no | `"abc123"` |

Returns an Anthropic XML system prompt block built from current Twin state: trust level, recent traces, session info, pending Elenchus claims, and pattern count. Deterministic for the same state.

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

### `resolve_verifications` — Actor-side Elenchus verification

```
resolve_verifications(verdicts)
```

| Param | Type | Required | Example |
|-------|------|----------|---------|
| `verdicts` | array | yes | `[{"claim_id": "abc", "verdict": true}]` |

The Actor evaluates pending Elenchus claims and submits boolean verdicts. Claims move to verified or rejected. Returns remaining pending count.

### `trigger_cognitive_recalibration` — Reset intake + trust

```
trigger_cognitive_recalibration()
```

No arguments. Resets the cognitive profile and trust score to zero. Use when the user indicates a major life or role change. Idempotent and re-triggerable.

### Setup

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cognitive-twin": {
      "command": "cognitive-twin"
    }
  }
}
```

### How It Works

- **Store**: Zero-encoding Hot Tier (FTS5, <0.2ms) + background SDR promotion to Warm Tier (ONNX BGE)
- **Recall**: Federated search across both tiers with score normalization and deduplication
- **Encoder**: ONNX Runtime BGE + CLS pooling + LSH -> 2048-bit SDR (Hamming correlation >= 0.95 with reference)
- **Container**: USD-Lite with 17 typed prim dataclasses + `.usda` serialization
- **Search**: XOR + popcount (Hamming distance) — sub-2ms warm recall
- **Routing**: Z-score surprise metric -> System 1 / System 2 dual-process
- **Learning**: Dual-mask Hebbian SDR evolution with homeostatic plasticity
- **Decay**: Lazy (computed on read, not background jobs)
- **Verification**: Elenchus GVR loop (trace-excluded, max 3 cycles) + v8 Actor-side deferral
- **Trust**: Continuous [0.0, 1.0] ledger gating Observer behavior into 3 tiers
- **Compaction**: Replay-then-archive with decay commutation invariant
- **Hot path**: Rust via PyO3 (`hippocampus` crate)

## The 33 Rules

The architecture is constrained by 33 inviolable rules covering biological fidelity (0W idle, 1-bit SDRs, lazy decay), verification integrity (trace exclusion, max 3 GVR cycles, verified-only consolidation), inquiry safeguards (apophenia guard, sincerity gate, rupture & repair), motor safety (inhibition default, one action at a time, RED kills everything), and Hebbian constraints (Merkle isolation, dual masks not XOR, homeostatic plasticity). These aren't guidelines — they're structural constraints enforced by 1,140+ tests across core + 5 sprints. See `CLAUDE.md` for the full specification.

## Philosophy

The Cognitive Twin is a self-evolving dialogue between a human and their externalized cognition, where both participants transform through the interaction, and the intelligence lives in the relationship — not in either party alone.

You own your mind. AI models just rent access to it.

## License

Proprietary. Copyright Joseph O. Ibrahim, 2026.
