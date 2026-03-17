# Phase 1 Design: Encoding & Hot Path (v8.0)
# Architect: Claude Opus 4.6 | Date: 2026-03-17
# Resolves: RISK-1 (Encoding Fidelity), TENSION-1 (Store vs Recall Latency)
# AND-chain blocker. Hardest subtask. Surface early, kill fast.

---

## 1. File Layout

```
python/cognitive_twin/hot_store/
├── __init__.py              # Public API: HotStore class, HotTrace dataclass
├── schema.py                # FTS5 table creation DDL, schema constants
└── promotion.py             # Hot → Warm promotion pipeline

python/cognitive_twin/encoder/
├── (semantic_encoder.py)    # EXISTING — DO NOT MODIFY
├── (__init__.py)            # EXISTING — DO NOT MODIFY
└── onnx_encoder.py          # NEW: ONNX Runtime wrapper for BGE-small

models/                      # gitignored, generated at build time
└── bge-small-en-v1.5.onnx   # Exported ONNX model

scripts/
└── export_onnx.py           # One-shot ONNX export + quantization

tests/test_hot_store/
├── __init__.py
├── conftest.py              # Fixtures: tmp_db, hot_store, sample traces
├── test_crud.py             # Store, retrieve, get_pending, mark_encoded
├── test_fts5.py             # Full-text search correctness + ranking
├── test_schema.py           # Schema idempotency, trigger integrity
└── test_promotion.py        # Hot → Warm promotion lifecycle

tests/test_onnx/
├── __init__.py
└── test_fidelity.py         # Gate 1a: 1000-trace Hamming correlation ≥ 0.95
```

### Frozen Boundary Compliance

- `crates/hippocampus/` — FROZEN. Warm Tier engine unchanged.
- `python/cognitive_twin/encoder/semantic_encoder.py` — EXISTING. Not modified.
- `python/cognitive_twin/encoder/__init__.py` — EXISTING. Not modified.
- `onnx_encoder.py` is a NEW file added alongside existing encoder files.

---

## 2. Hot Tier Schema (SQLite + FTS5)

### Table: `hot_traces`

```sql
CREATE TABLE IF NOT EXISTS hot_traces (
    trace_id    TEXT PRIMARY KEY,
    message     TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    domain      TEXT NOT NULL DEFAULT 'general',
    timestamp   REAL NOT NULL,
    encoded     INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS hot_traces_fts USING fts5(
    message,
    tags,
    domain,
    content='hot_traces',
    content_rowid='rowid'
);

-- Triggers keep FTS5 in sync with content table
CREATE TRIGGER IF NOT EXISTS hot_traces_ai AFTER INSERT ON hot_traces BEGIN
    INSERT INTO hot_traces_fts(rowid, message, tags, domain)
    VALUES (new.rowid, new.message, new.tags, new.domain);
END;

CREATE TRIGGER IF NOT EXISTS hot_traces_ad AFTER DELETE ON hot_traces BEGIN
    INSERT INTO hot_traces_fts(hot_traces_fts, rowid, message, tags, domain)
    VALUES ('delete', old.rowid, old.message, old.tags, old.domain);
END;

CREATE TRIGGER IF NOT EXISTS hot_traces_au AFTER UPDATE ON hot_traces BEGIN
    INSERT INTO hot_traces_fts(hot_traces_fts, rowid, message, tags, domain)
    VALUES ('delete', old.rowid, old.message, old.tags, old.domain);
    INSERT INTO hot_traces_fts(rowid, message, tags, domain)
    VALUES (new.rowid, new.message, new.tags, new.domain);
END;

-- Partial index: only un-encoded rows (promotion query is O(pending))
CREATE INDEX IF NOT EXISTS idx_hot_traces_pending
    ON hot_traces(encoded) WHERE encoded = 0;
```

### Design Rationale

- **FTS5 external content** (`content='hot_traces'`): FTS5 stores only the index,
  not duplicated data. Triggers keep it in sync.
- **`encoded` as INTEGER 0/1**: SQLite has no boolean type. Convention match.
- **`tags` as JSON text**: Matches v7 `tags_json TEXT` convention in traces table.
- **`timestamp` as REAL**: Unix epoch with sub-second precision. Matches v7.
- **Partial index on `encoded=0`**: Promotion scans only pending rows.
- **Same database file** (`data/twin.db`): Hot and Warm coexist. Separate tables.

---

## 3. API Signatures

### 3a. HotTrace Dataclass

```python
# python/cognitive_twin/hot_store/__init__.py

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

@dataclass
class HotTrace:
    """A trace in the Hot Tier (L1, zero-encoding)."""
    trace_id: str
    message: str
    tags: list[str]
    domain: str
    timestamp: float
    encoded: bool
```

### 3b. HotStore Class

```python
class HotStore:
    """SQLite + FTS5 Hot Tier for zero-latency trace storage.

    Provides immediate persistence without model loading or SDR encoding.
    Traces are stored as plaintext with full-text search indexing.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize HotStore with database path.

        Args:
            db_path: Path to SQLite database file.
        """

    def store(
        self,
        message: str,
        tags: list[str] | None = None,
        domain: str = "general",
        trace_id: str | None = None,
        timestamp: float | None = None,
    ) -> str:
        """Store a trace in the Hot Tier.

        Args:
            message: Trace content text.
            tags: Optional list of tag strings.
            domain: Knowledge domain (default: "general").
            trace_id: Optional explicit ID (generated UUID4 if None).
            timestamp: Optional explicit timestamp (time.time() if None).

        Returns:
            The trace_id of the stored trace.

        Raises:
            sqlite3.IntegrityError: If trace_id already exists.
        """

    def search(self, query: str, limit: int = 10) -> list[HotTrace]:
        """Full-text search over Hot Tier traces.

        Uses FTS5 MATCH syntax. Returns results ranked by BM25 relevance.

        Args:
            query: Search query string (FTS5 syntax).
            limit: Maximum results to return.

        Returns:
            List of matching HotTrace objects, ranked by relevance.
        """

    def get(self, trace_id: str) -> HotTrace | None:
        """Retrieve a single trace by ID.

        Args:
            trace_id: The trace ID to look up.

        Returns:
            HotTrace if found, None otherwise.
        """

    def get_pending(self, limit: int = 100) -> list[HotTrace]:
        """Retrieve traces pending SDR encoding (encoded=FALSE).

        Args:
            limit: Maximum traces to return.

        Returns:
            List of un-encoded HotTrace objects, oldest first.
        """

    def mark_encoded(self, trace_ids: list[str]) -> int:
        """Mark traces as promoted to Warm Tier.

        Args:
            trace_ids: List of trace IDs to mark as encoded.

        Returns:
            Number of traces actually updated.
        """

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to the database."""

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        """Create tables, FTS5 virtual table, triggers, and indexes if absent."""
```

### 3c. OnnxEncoder Class

```python
# python/cognitive_twin/encoder/onnx_encoder.py

from __future__ import annotations

import numpy as np

SDR_WIDTH = 2048
TARGET_ACTIVE_BITS = 80
PROJECTION_SEED = 42
EMBEDDING_DIM = 384

class OnnxEncoder:
    """ONNX Runtime encoder for BAAI/bge-small-en-v1.5.

    Produces SDR blobs matching SemanticEncoder's output within the
    fidelity gate (Hamming distance correlation ≥ 0.95).
    Same LSH projection matrix (seed=42, shape 2048×384).
    Model loads ONCE at __init__, not per-call.
    """

    def __init__(self, model_path: str) -> None:
        """Initialize ONNX encoder.

        Loads the ONNX model and tokenizer. This is the only time
        model loading happens — subsequent calls use the cached session.

        Args:
            model_path: Path to the .onnx model file.

        Raises:
            FileNotFoundError: If model_path does not exist.
            RuntimeError: If ONNX Runtime fails to load the model.
        """

    def encode(self, text: str) -> bytes:
        """Encode text to 256-byte SDR blob.

        Pipeline: text → tokenize → ONNX infer → 384-dim embedding →
        LSH projection (2048×384 matrix, seed=42) → top-80 bits →
        256-byte packed SDR.

        Args:
            text: Input text string.

        Returns:
            256-byte SDR blob (2048-bit, ~80 active bits).
        """

    def encode_batch(self, texts: list[str]) -> list[bytes]:
        """Batch-encode texts to SDR blobs.

        Args:
            texts: List of input text strings.

        Returns:
            List of 256-byte SDR blobs.
        """

    def _create_projection_matrix(self) -> np.ndarray:
        """Create LSH projection matrix (2048 × 384).

        Uses np.random.RandomState(PROJECTION_SEED) for determinism.
        MUST produce identical output to SemanticEncoder._create_projection_matrix().
        """

    def _tokenize(self, texts: list[str]) -> dict:
        """Tokenize texts for ONNX model input.

        Uses transformers.AutoTokenizer (loaded once at __init__).

        Args:
            texts: Input text strings.

        Returns:
            Dict of numpy arrays: input_ids, attention_mask, token_type_ids.
        """

    def _embedding_to_sdr(self, embedding: np.ndarray) -> bytes:
        """Convert 384-dim float embedding to 256-byte SDR blob.

        Steps:
        1. Project: projection_matrix @ embedding → 2048-dim scores
        2. Top-k: select top TARGET_ACTIVE_BITS indices
        3. Pack: set those bits in a 2048-bit array → 256 bytes

        Args:
            embedding: 384-dim float32 vector.

        Returns:
            256-byte SDR blob.
        """
```

### 3d. PromotionPipeline Class

```python
# python/cognitive_twin/hot_store/promotion.py

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cognitive_twin.encoder.onnx_encoder import OnnxEncoder
    from cognitive_twin.hot_store import HotStore

logger = logging.getLogger(__name__)

class PromotionPipeline:
    """Promotes traces from Hot Tier (L1) to Warm Tier (L2).

    Reads un-encoded traces from HotStore, encodes them via OnnxEncoder,
    writes SDR blobs to the warm-tier traces table, and marks
    hot traces as encoded.
    """

    def __init__(
        self,
        hot_store: HotStore,
        warm_db_path: str,
        encoder: OnnxEncoder,
    ) -> None:
        """Initialize promotion pipeline.

        Args:
            hot_store: HotStore instance for reading pending traces.
            warm_db_path: Path to warm-tier SQLite DB (existing traces table).
            encoder: OnnxEncoder instance (model already loaded).
        """

    def promote_batch(self, batch_size: int = 50) -> int:
        """Promote a batch of pending traces from Hot to Warm.

        Pipeline per trace:
        1. Read from hot_store.get_pending(batch_size)
        2. Encode message via OnnxEncoder.encode_batch() → SDR blobs
        3. INSERT into warm-tier traces table
        4. Mark hot traces as encoded

        All-or-nothing per batch: if encoding fails, no traces are marked.

        Args:
            batch_size: Maximum traces to promote in one batch.

        Returns:
            Number of traces promoted.
        """

    def _write_warm_trace(
        self,
        conn: sqlite3.Connection,
        trace_id: str,
        message: str,
        sdr_blob: bytes,
        tags: list[str],
        domain: str,
        timestamp: float,
    ) -> None:
        """Write a single trace to the warm-tier traces table.

        Uses the existing v7 traces table schema:
        - initial_strength=1.0, decay_lambda=0.05 (v7 defaults)
        - created_at=timestamp, last_accessed=timestamp
        - boosts_json='[]'

        Args:
            conn: Active SQLite connection.
            trace_id: Trace identifier.
            message: Original message text.
            sdr_blob: 256-byte SDR blob from OnnxEncoder.
            tags: Tag list.
            domain: Knowledge domain.
            timestamp: Original store timestamp.
        """
```

---

## 4. ONNX Export Pipeline

### scripts/export_onnx.py

One-shot script. Not part of the runtime. Run once to produce the model file.

```
Usage: python scripts/export_onnx.py [--quantize int8|fp16] [--output models/bge-small-en-v1.5.onnx]

Steps:
1. Load BAAI/bge-small-en-v1.5 via sentence-transformers
2. Extract the underlying PyTorch model
3. Create dummy input (tokenizer output for "hello world")
4. torch.onnx.export(model, dummy, output_path,
       input_names=["input_ids", "attention_mask", "token_type_ids"],
       output_names=["embeddings"],
       dynamic_axes={
           "input_ids": {0: "batch", 1: "seq"},
           "attention_mask": {0: "batch", 1: "seq"},
           "token_type_ids": {0: "batch", 1: "seq"},
       })
5. If --quantize=int8: onnxruntime.quantization.quantize_dynamic(
       model_input=fp32_path,
       model_output=output_path,
       weight_type=QuantType.QUInt8)
6. If --quantize=fp16: onnxconverter_common.float16.convert_float_to_float16(model)
7. Validate: load in ort.InferenceSession, run sanity check
8. Print model size and save
```

### Quantization Decision Tree (Gate 1a Sequence)

```
1. Export FP32 baseline ONNX
2. Quantize to INT8 (dynamic quantization — no training data needed)
3. Run Gate 1a fidelity test:
   a. Generate 1,000 trace messages (synthetic corpus)
   b. Encode all with SemanticEncoder (sentence-transformers, FP32) → SDR set A
   c. Encode all with OnnxEncoder (INT8) → SDR set B
   d. For 500 random trace pairs: compute Hamming(A_i, A_j) and Hamming(B_i, B_j)
   e. Pearson correlation(hamming_A, hamming_B) ≥ 0.95?
      YES → Ship INT8. Done.
      NO  → Step 4.
4. Quantize to FP16 instead. Re-run fidelity test.
   FP16 correlation ≥ 0.95?
      YES → Ship FP16. Done.
      NO  → BLOCKER: file at .agent-team/blockers/phase-1-encoding-fidelity.md
```

### Reference Corpus Design

1,000 synthetic traces covering:
- Short messages (5-10 words): "I had a productive meeting today"
- Medium messages (20-50 words): paragraph-length reflections
- Long messages (100+ words): detailed technical notes
- Domain diversity: personal, technical, emotional, factual
- Edge cases: single word, repeated words, unicode, numbers

The corpus is generated deterministically (seeded RNG for reproducibility).
Stored as a pytest fixture, not a file.

---

## 5. MCP Server Modification

### twin_store — Before (v7)

```python
@server.tool()
def twin_store(message: str, tags: list[str] | None = None, domain: str | None = None) -> str:
    # Loads SemanticEncoder → loads BGE model (SLOW, ~2-5s first call)
    # Encodes to SDR
    # Writes to warm-tier traces table
    semantic_store(DB_PATH, trace_id, message, tags, domain, source)
```

### twin_store — After (v8)

```python
_hot_store: Optional[HotStore] = None

def _get_hot_store() -> HotStore:
    """Lazy singleton for HotStore. No model loading."""
    global _hot_store
    if _hot_store is None:
        from cognitive_twin.hot_store import HotStore
        _hot_store = HotStore(str(DATA_DIR / "twin.db"))
    return _hot_store

@server.tool()
def twin_store(message: str, tags: list[str] | None = None, domain: str | None = None) -> str:
    """Store a memory trace. Zero-encoding hot path (<2ms)."""
    hot = _get_hot_store()
    trace_id = hot.store(
        message=message,
        tags=tags or [],
        domain=domain or "general",
    )
    return json.dumps({
        "status": "stored",
        "trace_id": trace_id,
        "tier": "hot",
        "encoded": False,
    }, default=str)
```

### Key Changes
- **No encoder import** in the store path
- **No model loading** — HotStore is pure SQLite
- **No SDR computation** — traces stored as plaintext
- **Response includes `tier` and `encoded`** — caller can see the trace is in L1
- **`_get_hot_store()` lazy singleton** — matches existing `_semantic_encoder` pattern

### What Stays
- `twin_recall` — unchanged for now (still warm-tier SDR search). Federated recall is Phase 6.
- `twin_patterns` — unchanged (reads from warm tier)
- `twin_session_status` — unchanged
- `twin_ask` — unchanged for now (killed in Phase 2)

---

## 6. Dependencies

### New dependencies (add to pyproject.toml):

```toml
dependencies = [
    # ... existing ...
    "onnxruntime>=1.17",
    "transformers>=4.36",  # AutoTokenizer for ONNX input
]
```

### Rationale
- `onnxruntime` — ONNX model inference. Replaces sentence-transformers in the encoding path.
- `transformers` — AutoTokenizer only. Already an implicit dependency via sentence-transformers.
- `sentence-transformers` — remains as existing dependency for reference encoder (Gate 1a tests
  and v7 warm-tier backward compat).

### Export-only dependencies (not in pyproject.toml):
- `torch` — needed only for `scripts/export_onnx.py` (one-shot export)
- `onnxconverter-common` — FP16 conversion (only if INT8 fails)

---

## 7. Gate Criteria (Crucible Reference)

### Gate 1a: Encoding Fidelity
- **Corpus:** 1,000 synthetic traces (seeded, deterministic)
- **Procedure:**
  1. Encode all traces with SemanticEncoder (sentence-transformers) → SDR set A
  2. Encode all traces with OnnxEncoder (ONNX Runtime) → SDR set B
  3. Select 500 random trace pairs (i, j)
  4. Compute Hamming(A_i, A_j) for each pair → vector H_ref
  5. Compute Hamming(B_i, B_j) for each pair → vector H_onnx
  6. Pearson correlation(H_ref, H_onnx) ≥ 0.95
- **Test file:** `tests/test_onnx/test_fidelity.py`
- **If fails:** INT8 → retry FP16. FP16 fail → BLOCKER.

### Gate 1b: Hot Path Latency
- **Store latency:** p99 < 2ms over 100 `hot_store.store()` calls
- **No model loading:** `twin_store` code path has zero imports from encoder/
  (verified by inspecting the import graph, not just timing)
- **FTS5 correctness:** Store 10 traces, search by keyword, verify correct results
- **Encoded flag:** All new traces have `encoded=FALSE`
- **Test files:** `tests/test_hot_store/test_crud.py`, `test_fts5.py`

---

## 8. Forge Implementation Order

```
Step  File                                    Verify After
─────────────────────────────────────────────────────────────
1     python/cognitive_twin/hot_store/schema.py       pytest tests/ -v --ignore=...
2     python/cognitive_twin/hot_store/__init__.py      pytest tests/ -v --ignore=...
3     tests/test_hot_store/conftest.py                 pytest tests/ -v --ignore=...
4     tests/test_hot_store/test_crud.py                pytest tests/test_hot_store/ -v
5     tests/test_hot_store/test_fts5.py                pytest tests/test_hot_store/ -v
6     tests/test_hot_store/test_schema.py              pytest tests/test_hot_store/ -v
7     python/cognitive_twin/encoder/onnx_encoder.py    pytest tests/ -v --ignore=...
8     scripts/export_onnx.py                           python scripts/export_onnx.py --quantize int8
9     tests/test_onnx/test_fidelity.py                 pytest tests/test_onnx/ -v
10    python/cognitive_twin/hot_store/promotion.py     pytest tests/ -v --ignore=...
11    tests/test_hot_store/test_promotion.py           pytest tests/test_hot_store/ -v
12    Modify python/cognitive_twin/mcp_server.py       pytest tests/ -v --ignore=...
13    Full regression                                  pytest tests/ -v --ignore=tests/test_encoder --ignore=tests/test_daemon
```

Each step creates a git commit: `v8-phase1: {description}`

---

## 9. Design Decisions & Rationale

### D1: Same SQLite file, separate table
Hot traces live in `hot_traces` table in `data/twin.db` (same file as warm-tier `traces` table).
Single database simplifies deployment and backup. SQLite handles concurrent reads from both
tables efficiently. Promotion pipeline reads hot_traces, writes to traces, marks hot_traces
as encoded — all within the same file.

### D2: FTS5 external content mode
FTS5 with `content='hot_traces'` avoids duplicating message text. The FTS5 virtual table stores
only the inverted index. Triggers keep it in sync. Standard SQLite pattern.

### D3: ONNX encoder as separate class, not patching SemanticEncoder
OnnxEncoder is a new class with the same interface contract (encode/encode_batch → bytes).
It does NOT inherit from or modify SemanticEncoder. This keeps frozen boundaries intact and
allows side-by-side fidelity comparison in Gate 1a.

### D4: Lazy singleton for HotStore in MCP server
Matches the existing `_semantic_encoder` lazy singleton pattern. HotStore creates the SQLite
schema on first use. No startup cost.

### D5: Promotion is batch-oriented, not per-trace
`promote_batch(batch_size=50)` processes up to 50 traces at once. This amortizes ONNX
inference overhead (batch inference is significantly faster than single-trace). The Observer
(Phase 2) calls this periodically.

### D6: Corpus uses pairwise Hamming correlation, not per-trace SDR equality
We don't require bit-for-bit identical SDRs between SemanticEncoder and OnnxEncoder.
ONNX quantization introduces minor embedding differences. What matters is that the
*relative distances* are preserved: traces that are semantically close should have similar
Hamming distances in both encoders. Pearson correlation of pairwise distances captures this.

---

## 10. Risk Mitigation

### Risk: INT8 quantization fails fidelity gate
**Mitigation:** FP16 fallback is pre-authorized (RISK-1 in ADR). FP16 payload is ~60-100MB,
acceptable for desktop hardware. No QAT attempt (spec explicitly forbids).

### Risk: ONNX export fails for BGE architecture
**Mitigation:** BGE-small-en-v1.5 is a standard BERT architecture. ONNX export for BERT models
is well-tested in the ecosystem. Dynamic axes handle variable sequence lengths.

### Risk: LSH projection matrix divergence
**Mitigation:** Both SemanticEncoder and OnnxEncoder use `np.random.RandomState(42)` with
shape `(2048, 384)`. The projection matrix is deterministic given the seed. Identical seed →
identical matrix → compatible SDRs (modulo embedding differences from quantization).

### Risk: FTS5 not available in SQLite build
**Mitigation:** FTS5 is enabled by default in Python's bundled SQLite since Python 3.7.
The schema creation will raise `sqlite3.OperationalError` if FTS5 is missing — fail fast.
