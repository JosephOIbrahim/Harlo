# Production Configuration — Harlo

## Starting the MCP Server

The MCP server is the entry point. Claude Desktop connects via `.mcp.json`.

```bash
# Default: runs with CognitiveEngine active
cognitive-twin

# Or manually:
python -m cognitive_twin.mcp_server
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGINE_ENABLED` | `1` | Master kill switch. `0` = pre-Sprint 3 behavior. |
| `USE_REAL_USD` | `1` | Use `pxr.Usd.Stage`. Falls back to dict mock if unavailable. |
| `OBSERVATION_LOGGING` | `1` | Emit CognitiveObservation on each exchange. |
| `PREDICTION_ENABLED` | `1` | Run XGBoost predictions. |
| `COGTWIN_LOG_LEVEL` | `INFO` | Python logging level. |

## Kill Switches

Each component can be disabled independently:

```bash
# Disable everything (pre-Sprint 3 behavior):
ENGINE_ENABLED=0 cognitive-twin

# Disable prediction only:
PREDICTION_ENABLED=0 cognitive-twin

# Disable observations only:
OBSERVATION_LOGGING=0 cognitive-twin

# Force mock stage (no USD):
USE_REAL_USD=0 cognitive-twin
```

## Data Locations

```
data/
├── stages/
│   ├── cognitive_twin.usda        # Root cognitive state (real USD)
│   └── delegates/
│       ├── claude.usda            # Claude delegate sublayer
│       └── claude_code.usda       # Claude Code delegate sublayer
├── observations.db                # SQLite observation buffer
├── twin.db                        # Core Twin database (traces, sessions)
└── trajectories_10k.jsonl         # Synthetic training data
models/
└── cognitive_predictor_v1.joblib  # XGBoost predictor (trained on 10K trajectories)
```

## Health Check

```bash
python scripts/health_check.py
```

Returns:
```json
{
  "engine": "active",
  "stage_type": "real_usd",
  "stage_file": true,
  "predictor": true,
  "observations_logged": 457,
  "exchange_index": 10,
  "delegates_registered": 2,
  "memory_queue_size": 0,
  "pending_save": false
}
```

## Graceful Degradation

The engine follows independent failure isolation:

| Component Failure | Behavior |
|-------------------|----------|
| USD import fails | Falls back to MockUsdStage (logged) |
| Model file missing | Prediction disabled (logged), rest works |
| DB locked | Observations queue in memory (max 100), drain on next success |
| DAG evaluation fails | Returns fallback response, MCP continues |
| Delegate cycle fails | Returns empty context, MCP continues |
| Stage save fails | Queued for retry on next exchange |

**The MCP server NEVER crashes from an engine failure.**

## Python Version Notes

- **Python 3.14** (.venv): All Sprint 1, 3, 5 code. USD falls back to MockUsdStage.
- **Python 3.12** (.venv312): All code + real USD 26.03. Full feature set.
- To run with real USD, use `.venv312/Scripts/python`.

## Backup Strategy

The `.usda` files are text. Back them up with git:

```bash
git add data/stages/*.usda data/stages/delegates/*.usda
git commit -m "backup: cognitive state snapshot"
```
