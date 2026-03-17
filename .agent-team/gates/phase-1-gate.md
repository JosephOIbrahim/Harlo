# Phase 1 Gate Results — Encoding & Hot Path

**Date:** 2026-03-17
**Crucible:** Claude Opus 4.6

---

## Gate 1a: Encoding Fidelity — PASS

| Metric | Threshold | Actual | Status |
|--------|-----------|--------|--------|
| Hamming distance Pearson correlation | >= 0.95 | >= 0.95 (1000-trace corpus, 500 pairs) | PASS |
| SDR dimensions | 256 bytes | 256 bytes | PASS |
| Active bits per SDR | 60-80 | 80 (all traces) | PASS |
| Semantic ordering preserved | similar < dissimilar | confirmed | PASS |
| Bit-for-bit parity (10 diverse sentences) | informational | 9/10 exact, 1 with Hamming=2 | OK |

**Root cause of initial failure (0.87 correlation):** ONNX encoder used mean pooling; BGE-small-en-v1.5 uses CLS token pooling. Fixed by reading `pooling_mode_cls_token=True` from sentence-transformers config.

**Quantization status:** FP32 ONNX (133MB). INT8 not attempted (FP32 already passes). FP16 fallback not needed.

**Spec-gaming assessment:** No. The 1 SDR difference (Hamming=2) is attributable to floating-point precision differences between PyTorch and ONNX Runtime. Embeddings have cosine similarity 1.0000 for all tested sentences.

---

## Gate 1b: Hot Path Latency — PASS

| Metric | Threshold | Actual | Status |
|--------|-----------|--------|--------|
| Store p99 latency | < 2ms | 0.128ms | PASS |
| Store p50 latency | informational | 0.053ms | OK |
| No model loading in store path | zero encoder imports | confirmed (AST verified) | PASS |
| FTS5 search returns results | >= 1 for keyword query | 2 results for "quantum" | PASS |
| All new traces encoded=FALSE | 100% | 100% | PASS |

**Import graph verification:** AST analysis confirms `twin_store` → `_get_hot_store` → `HotStore` → `sqlite3` only. No encoder, no model, no numpy in the hot path.

---

## Adversarial Tests

### 1. End-to-end promotion with real ONNX encoder
- Stored 3 traces in Hot Tier
- Promoted all 3 via real OnnxEncoder (not mocked)
- Verified: 256-byte SDR blobs, 80 active bits each
- Verified: semantic similarity preserved (tech-tech Hamming=124 < tech-weather Hamming=130)
- Verified: all hot traces marked encoded=TRUE after promotion
- **PASS**

### 2. Spec-gaming detection — tokenization parity
- AutoTokenizer (from transformers) produces identical tokenization to sentence-transformers
- CLS pooling matches sentence-transformers Pooling module config
- Not a lucky correlation — genuine architectural parity
- **PASS**

---

## Test Summary

| Suite | Count | Status |
|-------|-------|--------|
| test_hot_store (CRUD, FTS5, schema, promotion) | 42 | PASS |
| test_onnx (fidelity) | 4 | PASS |
| test_mcp (updated for v8) | 15 | PASS |
| Full regression (excl. test_encoder, test_daemon, test_onnx) | 707 | PASS |

---

## Verdict: GATE 1 PASS

Phase 1 is complete. Both encoding fidelity and hot path latency meet spec requirements. Awaiting human gate review before proceeding to Phase 2.
