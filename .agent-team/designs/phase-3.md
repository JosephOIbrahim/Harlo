# Phase 3 Design: Trust & Cognitive Profile (v8.0)
# Architect: Claude Opus 4.6 | Date: 2026-03-17
# Resolves: RISK-3 (3-Tier Float Trust), GAP-1 (Intake Migration)

---

## 1. Trust Ledger

### Schema
- `trust_score: float [0.0–1.0]` stored in SQLite
- Table: `trust_ledger (user_id TEXT PK, trust_score REAL, last_updated REAL)`
- Single user for v8.0 (user_id = "default")

### Thresholds (Basal Ganglia)
- 0.0–0.3: New — passive store only
- 0.3–0.7: Familiar — context/pattern surfacing
- 0.7–1.0: Trusted — proactive coaching/pushback

### Update Formula
- `delta = base_delta * session_quality`
- `session_quality = (0.4 * duration_factor + 0.3 * feedback_factor + 0.3 * correction_factor)`
- Positive: session > 3 exchanges, explicit positive feedback, accepted corrections
- Negative: explicit negative feedback, rejected suggestions
- Clamp to [0.0, 1.0]

---

## 2. TrustLedger API

```python
class TrustLedger:
    def __init__(self, db_path: str) -> None: ...
    def get_score(self, user_id: str = "default") -> float: ...
    def update(self, delta: float, user_id: str = "default") -> float: ...
    def get_tier(self, user_id: str = "default") -> str: ...
```

Tiers: "new" (< 0.3), "familiar" (0.3–0.7), "trusted" (>= 0.7)

---

## 3. Cognitive Recalibration

### MCP Tool: trigger_cognitive_recalibration
- Resets trust to 0.0
- Clears cognitive profile flag in SQLite
- Returns confirmation

### Schema
- Table: `cognitive_profile (user_id TEXT PK, intake_complete INTEGER, profile_json TEXT, last_calibrated REAL)`

---

## 4. Coach.md Integration
- Coach projection reads trust score and adjusts behavior directive
- New: minimal context; Familiar: full context; Trusted: proactive pushback

---

## 5. File Layout
```
python/cognitive_twin/trust/
├── __init__.py              # TrustLedger class
└── recalibration.py         # Recalibration logic

tests/test_trust/
├── __init__.py
└── test_trust.py

tests/test_recalibration/
├── __init__.py
└── test_recalibration.py
```
