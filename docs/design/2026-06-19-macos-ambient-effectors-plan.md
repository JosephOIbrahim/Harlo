# macOS Ambient Effectors — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When live biometrics flip the user into DEPLETED, Harlo autonomously
warms the display (a reversible, self-reverting "Harlo decides" lease) and offers
a Tier-2 Focus nudge — all through the existing Motor Cortex gate.

**Architecture:** A thin `Actuator` interface hides the macOS side (`shortcuts
run` + notification) so all trigger/gate/lease logic is pure-Python and TDD-able.
Effectors register as `executor` handlers; the trigger is edge-detected inside
`router._handle_biometric_ingest` (event-driven, Rule 1). Autonomous changes are
**leases** tracked in a JSON store and reverted on recovery / expiry / teardown.

**Tech Stack:** Python 3.12, `dataclasses`, `subprocess` (macOS `shortcuts` +
`osascript`), `pytest`. Reuses `motor/{consent,premotor,basal_ganglia,executor}`
and `modulation/allostatic`.

## Global Constraints

- **Rule 1:** no `sleep()`, no `while True`, no background threads, no polling —
  trigger + revert are event-driven off `biometric_ingest`.
- **Rule 9 / ADR-0001:** never persist raw biometric values; only derived state
  and the prior *setting*. The whole feature is gated by `ambient_effectors_enabled`
  (**default OFF**).
- **Rule 23/26:** every actuation goes through `basal_ganglia.gate()` via
  `executor.execute_one` — always.
- **Rule 28:** `execute_one` returns `HALTED` when `cognitive_state == "RED"`;
  RED never actuates (nudge-only).
- **`display_warmth` is `AUTONOMOUS(0)` + reversible; `set_focus` is `PER_ACTION(2)`.**
- Python 3.12; `ruff` line-length 100, `select = ["E4","E7","E9","F"]`.
- Run tests with `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest`.

---

## File Structure

- `python/harlo/motor/effectors/__init__.py` — package marker + public re-exports.
- `python/harlo/motor/effectors/actuator.py` — `ApplyResult`, `Actuator` Protocol,
  `FakeActuator` (test double), module-level `get_actuator()/set_actuator()`.
- `python/harlo/motor/effectors/leases.py` — `Lease`, JSON-file lease store
  (record / active / clear / expired).
- `python/harlo/motor/effectors/macos.py` — `MacOSActuator` (real adapter:
  `shortcuts run`, `osascript` notification).
- `python/harlo/motor/effectors/handlers.py` — `display_warmth` / `set_focus`
  handlers + `register_effectors()`.
- `python/harlo/motor/effectors/config.py` — `AmbientConfig` + `load_ambient_config`.
- `python/harlo/motor/effectors/trigger.py` — pure `decide_actuation(...)` +
  `decide_reverts(...)`.
- `python/harlo/daemon/router.py` — call the trigger from `_handle_biometric_ingest`.
- `python/harlo/motor/consent.py` — register the two new action types.
- `config/default_profile.yaml` — `ambient_effectors` block.
- Tests mirror under `tests/test_motor/test_effectors/`.

---

### Task 1: Consent registration for the new action types

**Files:**
- Modify: `python/harlo/motor/consent.py` (the `_ACTION_CONSENT_MAP` dict)
- Test: `tests/test_motor/test_effectors/test_consent_registration.py`

**Interfaces:**
- Consumes: `consent.get_consent_level`, `consent.ConsentLevel`.
- Produces: `_ACTION_CONSENT_MAP` now contains `"display_warmth"` and `"set_focus"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_consent_registration.py
from harlo.motor.consent import ConsentLevel, get_consent_level


def test_display_warmth_is_autonomous():
    # "Harlo decides" — fires without per-action consent, un-escalated by Rule 27.
    assert get_consent_level("display_warmth") == ConsentLevel.AUTONOMOUS


def test_set_focus_is_per_action():
    # Tier 2 — needs consent (nudge-to-confirm).
    assert get_consent_level("set_focus") == ConsentLevel.PER_ACTION
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_consent_registration.py -v`
Expected: `test_display_warmth_is_autonomous` FAILS — `get_consent_level` returns the default `PER_ACTION` for the unknown `"display_warmth"`.

- [ ] **Step 3: Register the action types**

In `python/harlo/motor/consent.py`, add two entries to `_ACTION_CONSENT_MAP`
(after the existing `"delete"` line, before the `LOCKED` block):

```python
    # macOS ambient effectors (docs/design/2026-06-19-macos-ambient-effectors)
    "display_warmth": ConsentLevel.AUTONOMOUS,   # Harlo decides: reversible, self-reverting
    "set_focus": ConsentLevel.PER_ACTION,        # Tier 2: nudge-to-confirm
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add python/harlo/motor/consent.py tests/test_motor/test_effectors/test_consent_registration.py
git commit -m "feat(effectors): register display_warmth (AUTONOMOUS) + set_focus (PER_ACTION)"
```

---

### Task 2: Actuator interface + FakeActuator

**Files:**
- Create: `python/harlo/motor/effectors/__init__.py` (empty)
- Create: `python/harlo/motor/effectors/actuator.py`
- Test: `tests/test_motor/test_effectors/test_actuator.py`

**Interfaces:**
- Produces:
  - `ApplyResult(ok: bool, tier: str, detail: str = "")` (frozen dataclass)
  - `Actuator` Protocol: `apply(self, action_type: str, params: dict) -> ApplyResult`,
    `revert(self, action_type: str, params: dict) -> bool`,
    `nudge(self, message: str) -> None`
  - `FakeActuator` with `.applied: list[tuple[str, dict]]`, `.reverted: list`,
    `.nudges: list[str]`
  - `get_actuator() -> Actuator`, `set_actuator(a: Actuator) -> None` (module global;
    defaults to a `FakeActuator` until `macos.install()` runs)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_actuator.py
from harlo.motor.effectors.actuator import (
    ApplyResult, FakeActuator, get_actuator, set_actuator,
)


def test_fake_records_apply_revert_nudge():
    fake = FakeActuator()
    r = fake.apply("display_warmth", {"shortcut": "Harlo Warm Display"})
    assert isinstance(r, ApplyResult) and r.ok is True and r.tier == "fake"
    assert fake.applied == [("display_warmth", {"shortcut": "Harlo Warm Display"})]
    assert fake.revert("display_warmth", {"shortcut": "Harlo Restore Display"}) is True
    assert fake.reverted == [("display_warmth", {"shortcut": "Harlo Restore Display"})]
    fake.nudge("rest?")
    assert fake.nudges == ["rest?"]


def test_actuator_is_swappable_global():
    fake = FakeActuator()
    set_actuator(fake)
    assert get_actuator() is fake
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_actuator.py -v`
Expected: FAIL — `ModuleNotFoundError: harlo.motor.effectors`.

- [ ] **Step 3: Create the package + actuator module**

```python
# python/harlo/motor/effectors/__init__.py
"""macOS ambient effectors (docs/design/2026-06-19-macos-ambient-effectors)."""
```

```python
# python/harlo/motor/effectors/actuator.py
"""Actuator interface — hides the macOS side so trigger/gate/lease logic is
pure-Python and testable. Rule 1: synchronous, event-driven, no threads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ApplyResult:
    ok: bool
    tier: str           # "harlo" | "shortcut" | "nudge" | "fake"
    detail: str = ""


@runtime_checkable
class Actuator(Protocol):
    def apply(self, action_type: str, params: dict) -> ApplyResult: ...
    def revert(self, action_type: str, params: dict) -> bool: ...
    def nudge(self, message: str) -> None: ...


class FakeActuator:
    """Test double — records calls, performs no I/O."""

    def __init__(self) -> None:
        self.applied: list[tuple[str, dict]] = []
        self.reverted: list[tuple[str, dict]] = []
        self.nudges: list[str] = []

    def apply(self, action_type: str, params: dict) -> ApplyResult:
        self.applied.append((action_type, params))
        return ApplyResult(ok=True, tier="fake")

    def revert(self, action_type: str, params: dict) -> bool:
        self.reverted.append((action_type, params))
        return True

    def nudge(self, message: str) -> None:
        self.nudges.append(message)


_ACTUATOR: Actuator = FakeActuator()


def get_actuator() -> Actuator:
    return _ACTUATOR


def set_actuator(actuator: Actuator) -> None:
    global _ACTUATOR
    _ACTUATOR = actuator
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add python/harlo/motor/effectors/__init__.py python/harlo/motor/effectors/actuator.py tests/test_motor/test_effectors/test_actuator.py
git commit -m "feat(effectors): Actuator interface + FakeActuator + swappable global"
```

---

### Task 3: Lease store (self-revert obligations)

**Files:**
- Create: `python/harlo/motor/effectors/leases.py`
- Test: `tests/test_motor/test_effectors/test_leases.py`

**Interfaces:**
- Produces:
  - `Lease(action_type: str, applied_at: float, max_duration_sec: float, params: dict)`
  - `record_lease(lease: Lease, *, path: Path) -> None`
  - `active_leases(*, path: Path) -> list[Lease]`
  - `clear_lease(action_type: str, *, path: Path) -> None`
  - `expired_leases(now: float, *, path: Path) -> list[Lease]`
- Rule 9: stores `params` (setting/shortcut names) + timestamps only — never
  biometric values.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_leases.py
from harlo.motor.effectors.leases import (
    Lease, record_lease, active_leases, clear_lease, expired_leases,
)


def test_record_then_active(tmp_path):
    p = tmp_path / "leases.json"
    record_lease(Lease("display_warmth", 100.0, 5400.0, {"restore": "X"}), path=p)
    got = active_leases(path=p)
    assert len(got) == 1 and got[0].action_type == "display_warmth"
    assert got[0].params == {"restore": "X"}


def test_clear_removes(tmp_path):
    p = tmp_path / "leases.json"
    record_lease(Lease("display_warmth", 100.0, 5400.0, {}), path=p)
    clear_lease("display_warmth", path=p)
    assert active_leases(path=p) == []


def test_expired_by_max_duration(tmp_path):
    p = tmp_path / "leases.json"
    record_lease(Lease("display_warmth", 100.0, 5400.0, {}), path=p)  # 90 min cap
    assert expired_leases(now=100.0 + 5399.0, path=p) == []           # not yet
    exp = expired_leases(now=100.0 + 5401.0, path=p)                  # past cap
    assert len(exp) == 1 and exp[0].action_type == "display_warmth"


def test_missing_file_is_empty(tmp_path):
    assert active_leases(path=tmp_path / "nope.json") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_leases.py -v`
Expected: FAIL — `ModuleNotFoundError: ...effectors.leases`.

- [ ] **Step 3: Implement the lease store**

```python
# python/harlo/motor/effectors/leases.py
"""Self-revert obligations for autonomous ("Harlo decides") effectors.

A lease is recorded when Harlo applies an autonomous, reversible setting and is
cleared when reverted. Atomic JSON write (temp + os.replace). Rule 9: setting
params + timestamps only — never biometric values."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Lease:
    action_type: str
    applied_at: float          # time.monotonic()-independent wall epoch seconds
    max_duration_sec: float    # backstop (default 90 min, set by caller)
    params: dict = field(default_factory=dict)


def _read(path: Path) -> list[Lease]:
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [Lease(**r) for r in rows]


def _write(path: Path, leases: list[Lease]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps([asdict(x) for x in leases]), encoding="utf-8")
    os.replace(tmp, path)


def record_lease(lease: Lease, *, path: Path) -> None:
    leases = [x for x in _read(path) if x.action_type != lease.action_type]
    leases.append(lease)
    _write(path, leases)


def active_leases(*, path: Path) -> list[Lease]:
    return _read(path)


def clear_lease(action_type: str, *, path: Path) -> None:
    _write(path, [x for x in _read(path) if x.action_type != action_type])


def expired_leases(now: float, *, path: Path) -> list[Lease]:
    return [x for x in _read(path) if now - x.applied_at > x.max_duration_sec]
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add python/harlo/motor/effectors/leases.py tests/test_motor/test_effectors/test_leases.py
git commit -m "feat(effectors): lease store for self-revert obligations"
```

---

### Task 4: Effector handlers + registration

**Files:**
- Create: `python/harlo/motor/effectors/handlers.py`
- Test: `tests/test_motor/test_effectors/test_handlers.py`

**Interfaces:**
- Consumes: `executor.register_handler`, `premotor.PlannedAction`,
  `actuator.get_actuator`, `leases.record_lease`, `leases.Lease`.
- Produces:
  - `handle_display_warmth(action: PlannedAction, session_state: dict) -> dict`
  - `handle_set_focus(action: PlannedAction, session_state: dict) -> dict`
  - `register_effectors() -> None` (idempotent; calls `register_handler`)
- `PlannedAction.payload` carries: `lease_path` (Path/str), `applied_at` (float),
  `max_duration_sec` (float), `apply_params` (dict), `message` (str, set_focus).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_handlers.py
from harlo.motor.effectors import handlers
from harlo.motor.effectors.actuator import FakeActuator, set_actuator
from harlo.motor.effectors.leases import active_leases
from harlo.motor.premotor import PlannedAction


def _action(action_type, payload):
    return PlannedAction(
        action_type=action_type, target=action_type, payload=payload,
        consent_level=0, reversible=True,
    )


def test_display_warmth_applies_and_records_lease(tmp_path):
    fake = FakeActuator(); set_actuator(fake)
    lp = tmp_path / "leases.json"
    act = _action("display_warmth", {
        "lease_path": str(lp), "applied_at": 100.0, "max_duration_sec": 5400.0,
        "apply_params": {"shortcut": "Harlo Warm Display", "restore": "Harlo Restore Display"},
    })
    out = handlers.handle_display_warmth(act, {})
    assert out["applied"] is True
    assert fake.applied == [("display_warmth",
                             {"shortcut": "Harlo Warm Display", "restore": "Harlo Restore Display"})]
    leases = active_leases(path=lp)
    assert len(leases) == 1 and leases[0].action_type == "display_warmth"


def test_set_focus_nudges(tmp_path):
    fake = FakeActuator(); set_actuator(fake)
    act = _action("set_focus", {"message": "Enable your wind-down Focus?"})
    out = handlers.handle_set_focus(act, {})
    assert out["nudged"] is True
    assert fake.nudges == ["Enable your wind-down Focus?"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_handlers.py -v`
Expected: FAIL — `ModuleNotFoundError: ...effectors.handlers`.

- [ ] **Step 3: Implement the handlers**

```python
# python/harlo/motor/effectors/handlers.py
"""Effector handlers, registered into the executor handler registry.

display_warmth ("Harlo decides", AUTONOMOUS): apply a bounded reversible change
and record a self-revert lease. set_focus (Tier 2, PER_ACTION): nudge-to-confirm
(the actuation is the user's named Shortcut, run only on their yes)."""

from __future__ import annotations

from pathlib import Path

from ..executor import register_handler
from ..premotor import PlannedAction
from .actuator import get_actuator
from .leases import Lease, record_lease

_REGISTERED = False


def handle_display_warmth(action: PlannedAction, session_state: dict) -> dict:
    p = action.payload
    result = get_actuator().apply("display_warmth", p["apply_params"])
    record_lease(
        Lease(
            action_type="display_warmth",
            applied_at=float(p["applied_at"]),
            max_duration_sec=float(p["max_duration_sec"]),
            params=p["apply_params"],
        ),
        path=Path(p["lease_path"]),
    )
    return {"applied": result.ok, "tier": result.tier}


def handle_set_focus(action: PlannedAction, session_state: dict) -> dict:
    get_actuator().nudge(action.payload["message"])
    return {"nudged": True}


def register_effectors() -> None:
    """Idempotent — safe to call on every daemon activation."""
    global _REGISTERED
    if _REGISTERED:
        return
    register_handler("display_warmth", handle_display_warmth)
    register_handler("set_focus", handle_set_focus)
    _REGISTERED = True
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add python/harlo/motor/effectors/handlers.py tests/test_motor/test_effectors/test_handlers.py
git commit -m "feat(effectors): display_warmth + set_focus handlers"
```

---

### Task 5: Ambient config (profile flag, default OFF)

**Files:**
- Create: `python/harlo/motor/effectors/config.py`
- Modify: `config/default_profile.yaml` (add an `ambient_effectors` block)
- Test: `tests/test_motor/test_effectors/test_config.py`

**Interfaces:**
- Produces:
  - `AmbientConfig(enabled: bool, warm_shortcut: str, restore_shortcut: str,
    focus_message: str, lease_max_sec: float)`
  - `load_ambient_config(profile: dict | None) -> AmbientConfig` — `None`/missing
    block → disabled defaults.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_config.py
from harlo.motor.effectors.config import AmbientConfig, load_ambient_config


def test_missing_block_is_disabled():
    cfg = load_ambient_config(None)
    assert isinstance(cfg, AmbientConfig) and cfg.enabled is False
    assert cfg.lease_max_sec == 5400.0  # 90 min default


def test_reads_block():
    cfg = load_ambient_config({"ambient_effectors": {
        "enabled": True, "warm_shortcut": "W", "restore_shortcut": "R",
        "focus_message": "rest?", "lease_max_sec": 1800.0,
    }})
    assert cfg.enabled is True and cfg.warm_shortcut == "W"
    assert cfg.restore_shortcut == "R" and cfg.lease_max_sec == 1800.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: ...effectors.config`.

- [ ] **Step 3: Implement config + add the profile block**

```python
# python/harlo/motor/effectors/config.py
"""Ambient-effector configuration. Rule 9: default OFF, per-capability opt-in."""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_LEASE_MAX_SEC = 5400.0  # 90 min backstop (~one ultradian cycle)


@dataclass(frozen=True)
class AmbientConfig:
    enabled: bool = False
    warm_shortcut: str = "Harlo Warm Display"
    restore_shortcut: str = "Harlo Restore Display"
    focus_message: str = "You're running low — enable your wind-down Focus?"
    lease_max_sec: float = _DEFAULT_LEASE_MAX_SEC


def load_ambient_config(profile: dict | None) -> AmbientConfig:
    block = (profile or {}).get("ambient_effectors") or {}
    base = AmbientConfig()
    return AmbientConfig(
        enabled=bool(block.get("enabled", base.enabled)),
        warm_shortcut=str(block.get("warm_shortcut", base.warm_shortcut)),
        restore_shortcut=str(block.get("restore_shortcut", base.restore_shortcut)),
        focus_message=str(block.get("focus_message", base.focus_message)),
        lease_max_sec=float(block.get("lease_max_sec", base.lease_max_sec)),
    )
```

Append to `config/default_profile.yaml`:

```yaml
# macOS ambient effectors (docs/design/2026-06-19-macos-ambient-effectors).
# OFF by default — Rule 9 / ADR-0001 opt-in. Enable per the runbook.
ambient_effectors:
  enabled: false
  warm_shortcut: "Harlo Warm Display"
  restore_shortcut: "Harlo Restore Display"
  focus_message: "You're running low — enable your wind-down Focus?"
  lease_max_sec: 5400.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add python/harlo/motor/effectors/config.py config/default_profile.yaml tests/test_motor/test_effectors/test_config.py
git commit -m "feat(effectors): AmbientConfig + default_profile block (default OFF)"
```

---

### Task 6: Trigger decision logic (pure, edge-detected)

**Files:**
- Create: `python/harlo/motor/effectors/trigger.py`
- Test: `tests/test_motor/test_effectors/test_trigger.py`

**Interfaces:**
- Consumes: `config.AmbientConfig`, `premotor.create_plan`, `premotor.ActionPlan`.
- Produces:
  - `plan_actuation(prior_depleted: bool, now_depleted: bool, cfg: AmbientConfig,
    *, lease_path: str, now: float) -> ActionPlan | None` — returns a 2-step plan
    (display_warmth + set_focus) only on the False→True edge while enabled; else `None`.
  - `plan_reverts(now_depleted: bool, cfg: AmbientConfig, *, lease_path: str,
    now: float) -> list[dict]` — revert descriptors (`{"action_type", "params"}`)
    for leases to undo (recovery OR expiry).
- Note: this module decides; the router executes (Task 7). Pure → fully testable.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_trigger.py
from harlo.motor.effectors.config import AmbientConfig
from harlo.motor.effectors.leases import Lease, record_lease
from harlo.motor.effectors import trigger

ON = AmbientConfig(enabled=True)


def test_edge_into_depleted_plans_two_steps(tmp_path):
    plan = trigger.plan_actuation(False, True, ON, lease_path=str(tmp_path / "l.json"), now=100.0)
    assert plan is not None
    kinds = [s.action_type for s in plan.steps]
    assert kinds == ["display_warmth", "set_focus"]


def test_no_edge_when_already_depleted(tmp_path):
    assert trigger.plan_actuation(True, True, ON, lease_path=str(tmp_path / "l.json"), now=100.0) is None


def test_disabled_never_plans(tmp_path):
    off = AmbientConfig(enabled=False)
    assert trigger.plan_actuation(False, True, off, lease_path=str(tmp_path / "l.json"), now=100.0) is None


def test_recovery_reverts_active_lease(tmp_path):
    p = tmp_path / "l.json"
    record_lease(Lease("display_warmth", 100.0, 5400.0, {"restore": "R"}), path=p)
    reverts = trigger.plan_reverts(False, ON, lease_path=str(p), now=200.0)  # recovered
    assert reverts == [{"action_type": "display_warmth", "params": {"restore": "R"}}]


def test_expiry_reverts_even_if_still_depleted(tmp_path):
    p = tmp_path / "l.json"
    record_lease(Lease("display_warmth", 100.0, 5400.0, {"restore": "R"}), path=p)
    reverts = trigger.plan_reverts(True, ON, lease_path=str(p), now=100.0 + 5401.0)
    assert len(reverts) == 1


def test_no_revert_while_depleted_and_unexpired(tmp_path):
    p = tmp_path / "l.json"
    record_lease(Lease("display_warmth", 100.0, 5400.0, {"restore": "R"}), path=p)
    assert trigger.plan_reverts(True, ON, lease_path=str(p), now=200.0) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_trigger.py -v`
Expected: FAIL — `ModuleNotFoundError: ...effectors.trigger`.

- [ ] **Step 3: Implement the trigger logic**

```python
# python/harlo/motor/effectors/trigger.py
"""Pure actuation/revert decision logic — edge-detected, no I/O beyond the
lease store. The router (Task 7) executes what this returns."""

from __future__ import annotations

from ..premotor import ActionPlan, create_plan
from .config import AmbientConfig
from .leases import active_leases, expired_leases


def plan_actuation(
    prior_depleted: bool,
    now_depleted: bool,
    cfg: AmbientConfig,
    *,
    lease_path: str,
    now: float,
) -> ActionPlan | None:
    if not cfg.enabled:
        return None
    if not (now_depleted and not prior_depleted):   # only the False->True edge
        return None
    steps = [
        {
            "action_type": "display_warmth",
            "reversible": True,
            "payload": {
                "lease_path": lease_path,
                "applied_at": now,
                "max_duration_sec": cfg.lease_max_sec,
                "apply_params": {
                    "shortcut": cfg.warm_shortcut,
                    "restore": cfg.restore_shortcut,
                },
            },
        },
        {
            "action_type": "set_focus",
            "reversible": True,
            "payload": {"message": cfg.focus_message},
        },
    ]
    return create_plan("ambient_wind_down", steps, is_depleted=now_depleted)


def plan_reverts(
    now_depleted: bool,
    cfg: AmbientConfig,
    *,
    lease_path: str,
    now: float,
) -> list[dict]:
    from pathlib import Path

    p = Path(lease_path)
    if not now_depleted:
        leases = active_leases(path=p)            # recovered → revert all
    else:
        leases = expired_leases(now, path=p)      # still depleted → only expired
    return [{"action_type": x.action_type, "params": x.params} for x in leases]
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 6 passed. (If `create_plan` rejects unknown payload
keys, confirm `premotor.create_plan` forwards `raw.get("payload")` into
`PlannedAction.payload` — it does in the current code; the step dict shape above
matches `raw.get("action_type")`, `raw.get("reversible")`, `raw.get("payload")`.)

- [ ] **Step 5: Commit**

```bash
git add python/harlo/motor/effectors/trigger.py tests/test_motor/test_effectors/test_trigger.py
git commit -m "feat(effectors): pure edge-detected actuation/revert decision logic"
```

---

### Task 7: Wire the trigger into the biometric_ingest path

**Files:**
- Modify: `python/harlo/daemon/router.py` (`_handle_biometric_ingest`, after the
  modulation-state writes)
- Test: `tests/test_motor/test_effectors/test_router_actuation.py`

**Interfaces:**
- Consumes: `effectors.config.load_ambient_config`, `effectors.trigger`,
  `effectors.handlers.register_effectors`, `effectors.actuator.get_actuator`,
  `executor.execute_one`, `consent.ConsentState`.
- Produces: a helper `run_ambient_effectors(prior_depleted, now_depleted,
  cognitive_state, cfg, *, lease_path, now, consent_state) -> dict` (summary:
  `{"actuated": [...], "reverted": [...], "halted": bool}`) called by the router.
  Keeping it a standalone function makes it unit-testable without the full router.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_motor/test_effectors/test_router_actuation.py
from harlo.motor.consent import ConsentState
from harlo.motor.effectors import handlers
from harlo.motor.effectors.actuator import FakeActuator, set_actuator
from harlo.motor.effectors.config import AmbientConfig
from harlo.motor.effectors.leases import Lease, record_lease, active_leases
from harlo.daemon.router import run_ambient_effectors

ON = AmbientConfig(enabled=True)


def _fresh(tmp_path):
    fake = FakeActuator(); set_actuator(fake)
    handlers.register_effectors()
    return fake, str(tmp_path / "l.json")


def test_edge_actuates_display_warmth(tmp_path):
    fake, lp = _fresh(tmp_path)
    out = run_ambient_effectors(False, True, "DEPLETED", ON,
                                lease_path=lp, now=100.0, consent_state=ConsentState())
    assert "display_warmth" in out["actuated"]
    assert ("display_warmth", {"shortcut": "Harlo Warm Display",
                               "restore": "Harlo Restore Display"}) in fake.applied
    assert len(active_leases(path=__import__("pathlib").Path(lp))) == 1


def test_red_halts_actuation(tmp_path):
    fake, lp = _fresh(tmp_path)
    out = run_ambient_effectors(False, True, "RED", ON,
                                lease_path=lp, now=100.0, consent_state=ConsentState())
    assert out["halted"] is True and out["actuated"] == []
    assert fake.applied == []


def test_set_focus_without_consent_nudges_not_actuates(tmp_path):
    fake, lp = _fresh(tmp_path)
    run_ambient_effectors(False, True, "DEPLETED", ON,
                          lease_path=lp, now=100.0, consent_state=ConsentState())
    # PER_ACTION with no grant → gate withholds the Shortcut; user is nudged.
    assert fake.nudges == ["You're running low — enable your wind-down Focus?"]


def test_recovery_reverts(tmp_path):
    from pathlib import Path
    fake, lp = _fresh(tmp_path)
    record_lease(Lease("display_warmth", 100.0, 5400.0,
                       {"shortcut": "Harlo Warm Display", "restore": "Harlo Restore Display"}),
                 path=Path(lp))
    out = run_ambient_effectors(True, False, "NORMAL", ON,
                                lease_path=lp, now=200.0, consent_state=ConsentState())
    assert "display_warmth" in out["reverted"]
    assert active_leases(path=Path(lp)) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_router_actuation.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_ambient_effectors'`.

- [ ] **Step 3: Implement `run_ambient_effectors` and call it from the ingest handler**

Add to `python/harlo/daemon/router.py` (top-level function):

```python
def run_ambient_effectors(
    prior_depleted: bool,
    now_depleted: bool,
    cognitive_state: str,
    cfg,                       # effectors.config.AmbientConfig
    *,
    lease_path: str,
    now: float,
    consent_state=None,
) -> dict:
    """Apply/revert ambient effectors for one biometric_ingest. Event-driven
    (Rule 1). RED halts via execute_one (Rule 28). Best-effort: a failure here
    must never reject the ingest."""
    from ..motor.consent import ConsentState
    from ..motor.executor import execute_one, ExecutionStatus
    from ..motor.effectors import trigger
    from ..motor.effectors.actuator import get_actuator
    from ..motor.effectors.handlers import register_effectors
    from ..motor.effectors.leases import clear_lease
    from pathlib import Path

    register_effectors()
    consent_state = consent_state or ConsentState()
    session_state = {"cognitive_state": cognitive_state}
    summary = {"actuated": [], "reverted": [], "halted": False}

    # 1. Reverts first (recovery or expiry) — restore before any new apply.
    for rev in trigger.plan_reverts(now_depleted, cfg, lease_path=lease_path, now=now):
        get_actuator().revert(rev["action_type"], rev["params"])
        clear_lease(rev["action_type"], path=Path(lease_path))
        summary["reverted"].append(rev["action_type"])

    # 2. Apply on the False->True edge.
    plan = trigger.plan_actuation(prior_depleted, now_depleted, cfg,
                                  lease_path=lease_path, now=now)
    if plan is None:
        return summary
    for step in plan.steps:
        result = execute_one(step, session_state, consent_state)
        if result.status == ExecutionStatus.HALTED:
            summary["halted"] = True
            break
        if result.status == ExecutionStatus.SUCCESS:
            summary["actuated"].append(step.action_type)
        else:
            # Gated (e.g. set_focus PER_ACTION without consent) → nudge instead.
            if step.action_type == "set_focus":
                get_actuator().nudge(cfg.focus_message)
    return summary
```

Then, inside `_handle_biometric_ingest`, AFTER the existing modulation-state
writes and BEFORE `return {...}`, add (reading the prior depleted flag from the
persisted modulation state you already load/compute):

```python
    # Ambient effectors (docs/design/2026-06-19-macos-ambient-effectors).
    # Best-effort; never rejects the ingest. prior_depleted = the value persisted
    # before this ingest overwrote it.
    try:
        import time as _t
        from ..config import PROFILE_PATH
        from ..modulation.effector_leases_path import ambient_lease_path  # see note
        from ..motor.effectors.config import load_ambient_config
        import yaml
        profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8")) or {}
        cfg = load_ambient_config(profile)
        if cfg.enabled:
            run_ambient_effectors(
                prior_depleted=bool(prior_depleted),
                now_depleted=bool(depleted),
                cognitive_state=cognitive,
                cfg=cfg,
                lease_path=str(ambient_lease_path()),
                now=_t.time(),
            )
    except Exception:  # noqa: BLE001 — effectors are advisory
        pass
```

Add the lease-path helper:

```python
# python/harlo/modulation/effector_leases_path.py
"""Single source of truth for the effector lease-store path (in DATA_DIR)."""
from ..daemon.config import DATA_DIR
from pathlib import Path


def ambient_lease_path() -> Path:
    return DATA_DIR / "effector_leases.json"
```

> NOTE: `prior_depleted` must be read from the persisted modulation state
> *before* the existing code overwrites it. If the current `_handle_biometric_ingest`
> overwrites first, hoist a `prior = read_modulation_state(...)` read to the top of
> the handler and pass `prior.is_depleted` as `prior_depleted`.

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 4 passed.

- [ ] **Step 5: Run the full modulation + motor + daemon suite (no regressions)**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor tests/test_modulation tests/test_daemon -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add python/harlo/daemon/router.py python/harlo/modulation/effector_leases_path.py tests/test_motor/test_effectors/test_router_actuation.py
git commit -m "feat(effectors): wire ambient actuation into biometric_ingest (edge-triggered, RED-halts)"
```

---

### Task 8: MacOSActuator (real adapter) + install hook

**Files:**
- Create: `python/harlo/motor/effectors/macos.py`
- Test: `tests/test_motor/test_effectors/test_macos_actuator.py`

**Interfaces:**
- Consumes: `actuator.Actuator`, `actuator.ApplyResult`, `actuator.set_actuator`.
- Produces: `MacOSActuator` (real); `install() -> None` (sets the global actuator
  to a `MacOSActuator` when `sys.platform == "darwin"`).

- [ ] **Step 1: Write the failing test (subprocess mocked — no real OS calls)**

```python
# tests/test_motor/test_effectors/test_macos_actuator.py
from unittest.mock import patch
from harlo.motor.effectors.macos import MacOSActuator


def test_apply_runs_warm_shortcut():
    a = MacOSActuator()
    with patch("harlo.motor.effectors.macos.subprocess.run") as run:
        run.return_value.returncode = 0
        r = a.apply("display_warmth", {"shortcut": "Harlo Warm Display", "restore": "x"})
    assert r.ok is True and r.tier == "shortcut"
    run.assert_called_once_with(
        ["shortcuts", "run", "Harlo Warm Display"], capture_output=True, timeout=10,
    )


def test_revert_runs_restore_shortcut():
    a = MacOSActuator()
    with patch("harlo.motor.effectors.macos.subprocess.run") as run:
        run.return_value.returncode = 0
        ok = a.revert("display_warmth", {"restore": "Harlo Restore Display"})
    assert ok is True
    run.assert_called_once_with(
        ["shortcuts", "run", "Harlo Restore Display"], capture_output=True, timeout=10,
    )


def test_nudge_uses_osascript():
    a = MacOSActuator()
    with patch("harlo.motor.effectors.macos.subprocess.run") as run:
        run.return_value.returncode = 0
        a.nudge("rest?")
    args = run.call_args[0][0]
    assert args[0] == "osascript" and "display notification" in args[2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=python PYTHONOPTIMIZE=0 .venv312/bin/python -m pytest tests/test_motor/test_effectors/test_macos_actuator.py -v`
Expected: FAIL — `ModuleNotFoundError: ...effectors.macos`.

- [ ] **Step 3: Implement the macOS adapter**

```python
# python/harlo/motor/effectors/macos.py
"""Real macOS actuator: Tier-2 `shortcuts run` + `osascript` notification.
Direct (Tier-3 private-framework) control is intentionally NOT here — it is an
opt-in, non-sandboxed follow-up (spec §12)."""

from __future__ import annotations

import subprocess
import sys

from .actuator import ApplyResult, set_actuator


def _run_shortcut(name: str) -> bool:
    try:
        cp = subprocess.run(
            ["shortcuts", "run", name], capture_output=True, timeout=10,
        )
        return cp.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class MacOSActuator:
    def apply(self, action_type: str, params: dict) -> ApplyResult:
        ok = _run_shortcut(params["shortcut"])
        return ApplyResult(ok=ok, tier="shortcut")

    def revert(self, action_type: str, params: dict) -> bool:
        return _run_shortcut(params["restore"])

    def nudge(self, message: str) -> None:
        script = f'display notification "{message}" with title "Harlo"'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass


def install() -> None:
    """Install the real actuator on macOS; no-op elsewhere (keeps the fake)."""
    if sys.platform == "darwin":
        set_actuator(MacOSActuator())
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: 3 passed.

- [ ] **Step 5: Wire `install()` at daemon startup**

In `python/harlo/daemon/main.py`, inside `run_socket_activated()` after
`ensure_data_dirs()`, add:

```python
    try:
        from ..motor.effectors.macos import install as _install_effectors
        _install_effectors()
    except Exception:
        pass
```

- [ ] **Step 6: Commit**

```bash
git add python/harlo/motor/effectors/macos.py python/harlo/daemon/main.py tests/test_motor/test_effectors/test_macos_actuator.py
git commit -m "feat(effectors): MacOSActuator (shortcuts run + osascript) + startup install"
```

---

### Task 9: Manual integration verification (on the Mac)

**Files:** none (runbook). This is a real verification, not a placeholder.

- [ ] **Step 1:** In Shortcuts.app, create two shortcuts: **"Harlo Warm Display"**
  (e.g. *Set Night Shift → On*) and **"Harlo Restore Display"** (*Set Night Shift
  → Off*). Optionally a wind-down Focus shortcut.
- [ ] **Step 2:** Enable the feature: set `ambient_effectors.enabled: true` in the
  active profile (or the user data-dir copy).
- [ ] **Step 3:** Confirm `shortcuts run "Harlo Warm Display"` warms the display
  from a terminal.
- [ ] **Step 4:** Drive a DEPLETED transition end-to-end (XPC ingest of a
  high-HR/low-HRV batch, as in the Phase 5B proof) and confirm: display warms,
  a Focus nudge appears, `~/Library/Application Support/Harlo/effector_leases.json`
  has one lease.
- [ ] **Step 5:** Send a normal batch (recovery) and confirm the display restores
  and the lease file is empty.
- [ ] **Step 6:** Compliance: `make compliance-greps` stays green; confirm no raw
  biometric values appear in `effector_leases.json`.

---

## Self-Review

- **Spec coverage:** §3 architecture (Tasks 4,6,7,8) · §4 bands→ConsentLevel
  (Task 1) · §5 rails: self-revert (Tasks 3,6,7), bounded magnitude (the
  Harlo-authored shortcut, Task 9), announce/undo (nudge Task 4/8; full button
  UX deferred — see note), back-off (deferred to Phase 2, listed below) · §6
  tiered backend (Tasks 4,8) · §7 trigger+revert (Tasks 6,7) · §8 Rule 1/9/28
  (Tasks 5,6,7,8) · §10 Phase 1 scope (all) · §11 tests (each task) · §13 lease
  90-min + recovery/expiry (Tasks 3,6,7).
- **Deferred from §5 to Phase 2 (documented, not silent):** rail #3 interactive
  `[keep][undo][stop]` buttons (needs the bridge app UI — v1 ships a basic
  notification + recovery-revert) and rail #4 back-off-on-override (needs a way to
  read the user's manual setting change; not available via the Shortcut path).
  These are the only spec items not in this plan.
- **Placeholder scan:** none — every code step is complete and runnable.
- **Type consistency:** `ApplyResult(ok, tier, detail)`, `Actuator.{apply,revert,
  nudge}`, `Lease(action_type, applied_at, max_duration_sec, params)`,
  `plan_actuation/plan_reverts`, `run_ambient_effectors(...)` signatures match
  across Tasks 2–8.

## Execution Handoff

Two execution options — see below.
