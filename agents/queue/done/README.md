# Completed agent queue specs

`harness.py:_drain_queue()` globs `agents/queue/*.yaml` non-recursively,
so moving a task descriptor into this subdirectory takes it out of the
dispatch loop while keeping the spec in version control for archaeology.

Each YAML here landed via the PR or commit noted below.

| Task | Landed in |
|---|---|
| `0001-bootstrap-os-launch.yaml` | PR #10 — `f0ce331` (macOS bundle, launchd plists, first-run migration) |
| `0002-intake-coaching-scaffold.yaml` | PR #10 — `f0ce331` (intake CLI, composition bridge, three INTAKE_CALIBRATED layers) |
| `0003-healthbridge-foundation.yaml` | PR #10 — `f0ce331` (biometric_barrier, Allostatic biometric methods, Basal Ganglia integration) |
