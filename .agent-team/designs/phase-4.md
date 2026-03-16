# Phase 4 Design: Observation + Intake + Migration + Bridge Deletion

**Phase:** 4
**Gates:** 4a, 4b, 4c, 4d, 4e

## Strategy

1. Build `skills/` observer (incremental, ghost-window safe)
2. Build `intake/` cognitive profile system (continuous scoring, semantic ceiling)
3. Build `migrate_v7.py` (bootstrap /Skills from legacy)
4. Move bridge submodules into brainstem (absorb functionality)
5. Delete bridge/ entirely, fix all imports
6. Register twin_skills + twin_intake MCP tools
7. Update all tests

## Module Layout

```
python/cognitive_twin/skills/
├── __init__.py
└── observer.py          # Incremental skills observer

python/cognitive_twin/intake/
├── __init__.py
├── questionnaire.py     # Adaptive intake questions
└── multipliers.py       # Continuous scoring + derivation

python/cognitive_twin/migrate_v7.py  # Migration script
```

## Bridge Absorption Plan

Bridge submodules → brainstem:
- generate.py → brainstem/generate.py
- escalation.py → brainstem/escalation.py (already partially there)
- amygdala.py → brainstem/amygdala.py
- consolidation.py → brainstem/consolidation.py
- intent_check.py → brainstem/intent_check.py
- epistemological_bypass.py → brainstem/epistemological_bypass.py
- reflex_compiler.py → brainstem/reflex_compiler.py
- integrity.py → brainstem/integrity.py (already have merkle.py)

Import updates: mcp_server.py, daemon/router.py, all test files.
