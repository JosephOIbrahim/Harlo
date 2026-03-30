# Update README.md to v8.0.0

## Context

The Cognitive Twin codebase just completed a v8.0.0 rewrite (791 tests, 0 failures, all 7 phases in AGENTS.md complete). The README.md and its mermaid diagrams are stale — they reflect v7.0.0 architecture. Update everything to accurately represent the current v8.0.0 system.

## Step 1: Read current state

Read these files to build full context of what changed:
- `README.md` (current — this is what you're updating)
- `AGENTS.md` (v8 implementation spec — this is your source of truth for what's new)
- `CLAUDE.md` (the 33 rules — architectural constraints)
- `CHANGELOG.md` or any version history
- `pyproject.toml` (version, entry points, dependencies)
- `.mcp.json` (current MCP tool registry)
- `src/` directory tree
- Skim key v8 modules:
  - `python/cognitive_twin/hot_store/__init__.py`
  - `python/cognitive_twin/federated_recall.py`
  - `python/cognitive_twin/observer/__init__.py`
  - `python/cognitive_twin/coach/__init__.py`
  - `python/cognitive_twin/trust/__init__.py`
  - `python/cognitive_twin/compaction/__init__.py`
  - `python/cognitive_twin/elenchus_v8/__init__.py`
  - `python/cognitive_twin/encoder/onnx_encoder.py`

## Step 2: Identify what's stale in the README

Compare README content against actual v8 codebase. Flag:
- Architecture diagrams that don't show Hot/Warm tiers, Observer, Coach, federated recall
- MCP tool registry that's missing new tools or still lists deleted tools (twin_ask)
- Any v7 descriptions that don't reflect v8 changes (e.g., twin_store is now zero-encoding hot tier)
- Version numbers still showing v7
- Test counts still showing 720 instead of 791
- Missing subsystems (Trust Ledger, Temporal Compaction, ONNX encoder)

## Step 3: Update mermaid diagrams

Every mermaid diagram in the README must be updated to reflect v8 architecture. Specifically:

### Architecture Overview Diagram
Must now show:
- **Hot Tier** (FTS5, zero-encoding) and **Warm Tier** (SDR-encoded) as distinct storage layers
- **Observer** process (background Hot→Warm promotion, no LLM dependency)
- **Coach** (system prompt projection to Actor)
- **Federated Recall** (query_past_experience merging both tiers)
- **Actor/Observer split** — Actor is the LLM (Claude), Observer is the Twin
- **Trust Ledger** gating Observer behavior
- **ONNX Encoder** in the encoding pipeline
- **Elenchus v8 deferral** — Observer queues claims, Actor resolves

### Data Flow Diagram
Must show the two-path flow:
1. **Store path:** User message → Actor (Claude) → MCP twin_store → Hot Tier (FTS5, instant) → Observer promotes → Warm Tier (SDR via ONNX)
2. **Recall path:** query_past_experience → parallel FTS5 search + SDR Hamming search → score normalization → deduplication → merged ranked results

### Memory Lifecycle Diagram
Must show the full lifecycle:
- Store (hot) → Promote (observer) → Decay (lazy exponential) → Hebbian evolution (strengthen/weaken masks) → Reconsolidation (user retrieval boost) → Compaction (temporal) → Apoptosis (physical deletion + VACUUM)

### MCP Tool Diagram
Must reflect the final v8 tool registry:
- twin_store (MODIFIED — hot tier, zero-encoding)
- twin_recall (KEPT — warm-tier SDR, backward compat)
- query_past_experience (NEW — federated Hot+Warm)
- twin_coach (NEW — system prompt projection)
- twin_patterns (KEPT)
- twin_session_status (KEPT)
- resolve_verifications (NEW — Actor-side Elenchus)
- trigger_cognitive_recalibration (NEW — intake reset)
- twin_ask (DELETED)

### Verification Pipeline Diagram (Elenchus)
Must show the v8 deferral model:
- Observer runs structural/heuristic checks locally
- Semantic claims queued to ElenchusQueue
- Coach Core surfaces pending claims in Actor's system prompt
- Actor calls resolve_verifications with boolean verdicts
- Verdicts flow back to Observer for consolidation

### USD-Lite Composition Diagram
If present, should reflect the 17 typed prims and LIVRPS resolution order.

## Step 4: Update README prose

- Update version to v8.0.0
- Update test count to 791
- Update the MCP tool table
- Add sections for new subsystems if not present (Hot/Warm tiering, Observer, Coach, Trust, Compaction, ONNX encoding, Elenchus v8 deferral)
- Update any installation/quickstart instructions if entry points changed
- Update any dependency lists (onnxruntime added, sentence-transformers may be optional now for hot path)
- Ensure the "How It Works" or equivalent section tells the v8 story: zero-latency hot storage, background promotion, federated recall, actor/observer split

## Step 5: Verify

After editing, do a final read of the updated README.md and verify:
- Every mermaid diagram renders valid mermaid syntax (no broken arrows, no unclosed blocks)
- No references to twin_ask (deleted)
- No stale v7 test counts or version numbers
- The MCP tool table matches `.mcp.json`
- The architecture description matches what the code actually does
- All new v8 subsystems are represented in both diagrams AND prose

## Rules

- Keep the README's existing structure and style. Don't rewrite from scratch — update what's there.
- Mermaid diagrams should be clean and readable. Use subgraphs for logical grouping. Use consistent arrow styles.
- If the existing README has sections that are already accurate for v8, leave them alone.
- If you're unsure whether something changed, read the actual source file before deciding.
- The README is the first thing a developer or investor sees. It needs to be accurate and impressive.
