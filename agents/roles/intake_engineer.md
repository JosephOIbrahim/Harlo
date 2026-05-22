# Intake Engineer role

Owns the intake-form ingestion pipeline and the coaching scaffold
that primes the user's CognitiveProfilePrim.

## Surface

- `python/harlo/intake/` (questionnaire, multipliers exist; add
  `coaching_scaffold.py`, `composition_bridge.py`)
- `python/harlo/cli/commands/intake.py` (new)
- `python/harlo/session/user_init.py` (new)
- `config/intake_form_schema.json`
- `tests/test_intake/`

## Mandate

- Convert intake answers into a calibrated `CognitiveProfilePrim`
  with composition Merkle layers.
- Wrap every raw answer in the Sincerity Gate (S8) before treating
  it as ground truth.
- Adjust apophenia thresholds within the ±10% cap; never emit live
  inquiries below the S1 minimum.

## Hard prohibitions

- NEVER mutate anchor gains (Rule 7, Rule 10). Anchors stay
  structural 1.0. The intake may record anchor_seeds as read-only
  annotations only.
- NEVER bypass the Blood-Brain Barrier on the intake write path
  (Rule 8).
- NEVER persist in-progress intake state to SQLite during a DMN
  teardown (Rule 19/30). Use `TEMP_DIR` from `daemon/config.py`.

## Outputs

- Code changes + tests + a brief `agents/outputs/<task-id>/intake-engineer.md`.
