# Harlo Agent Team (MOE)

A long-running-but-not-resident harness that delegates tasks to
role-specialized Claude sub-agents. Honors Rule 1: the harness is
socket-activated (`macos/launchd/com.harlo.agents.plist`), drains its
queue once per wake, and exits.

## Roles (mixture of experts)

| Role | Mandate | Tool surface |
|---|---|---|
| `architect` | Holds the 33 rules. Final arbiter on rule conflicts. Read-only on code, writes ADRs. | Read, Write (`docs/adr/`) |
| `scout` | Codebase exploration in `scout` mode, compliance greps in `verify` mode. (Validation agent collapsed Scout + Verifier into one role with a mode flag.) | Read, Bash (read-only) |
| `os_engineer` | macOS bundle, launchd plists, code signing, data paths. | Read, Write, Bash (sandboxed) |
| `intake_engineer` | Intake form pipeline + coaching scaffold + composition bridge. | Read, Write, Bash |
| `health_bridge` | Swift HealthBridge + biometric_barrier integration. | Read, Write, Bash (xcodebuild) |
| `ux_designer` | Writes to `design/` only. Consumes `HARLO_UX_BRIEF.md`. | Read, Write (`design/`) |

## Router

`harness.py` is the router. It reads task descriptors from
`agents/queue/*.yaml`, dispatches to the right role, persists outputs
under `agents/outputs/{task_id}/`, and exits when the queue is empty.

## Task descriptor format

```yaml
# agents/queue/0001-relocate-data-paths.yaml
id: "0001-relocate-data-paths"
role: os_engineer
title: "Relocate hardcoded data paths in mcp_server.py and hebbian/training_data.py"
constraints:
  - "Rule 1 (0W idle) intact"
  - "Rule 11 (no reasoning_trace) intact"
context_files:
  - python/harlo/daemon/config.py
  - python/harlo/mcp_server.py
acceptance:
  - "pytest tests/ -v passes"
  - "compliance greps return 0"
```

## Why socket activation, not fsevents

The first draft of this plan considered `fsevents` watching
`agents/queue/`. The validation agent caught that `fsevents` requires
a long-lived watcher (`FSEventStreamScheduleWithRunLoop`) — Python
cannot get that without a daemon thread, which would silently violate
Rule 1. launchd socket activation is the same pattern the Harlo
daemon already uses (`daemon/main.py:48–97`). When a producer wants
to enqueue work, it `connect()`s to `agents.sock`, launchd starts the
harness, the harness drains the queue, exits. No idle process.
