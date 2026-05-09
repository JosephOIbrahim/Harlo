# MCP Daemon Lifecycle

Reference doc for the `harlo` MCP server's process model, death triggers,
and reconnect behavior inside Claude Code. Smoke-test authors use this to
plan deterministic recovery.

All claims here cite either a source line or a recorded experiment from the
diagnostic session on 2026-05-09 against PID 1461 → 2568 (M1 Mac Studio,
macOS 26, Claude Code parent PID 1447).

---

## Process Model

The `harlo` MCP server is a **stdio transport** child process spawned by
Claude Code per session. It is launched via the console script
`harlo` → `harlo.mcp_server:main` (`pyproject.toml [project.scripts]`),
which terminates with `server.run(transport="stdio")` at
`python/harlo/mcp_server.py:626`. The MCP server has **no listening
socket, no launchd plist, and no socket activation** in the path used by
Claude Code; the unrelated `python/harlo/daemon/main.py:48` socket-activation
code path is the v3 IPC daemon — still live for CLI use via
`python/harlo/cli/ipc.py:59` (`_direct_execute` → `run_direct`) — and is a
separate process from the MCP entry point. Smoke-test authors should not
conflate the two: this doc covers the MCP server only.

Verified config (`~/.claude.json`):

```json
"harlo": {
  "type": "stdio",
  "command": "/Users/rustybeard/Code/Harlo/.venv314/bin/harlo",
  "args": [],
  "env": {"USE_REAL_USD": "1"}
}
```

Verified FD layout of a running daemon (`lsof -p 1461`):

```
0u unix  -> stdin pipe to Claude Code
1u unix  -> stdout pipe to Claude Code
2u unix  -> stderr pipe to Claude Code
3u KQUEUE
4u/5u unix socketpair (internal)
```

No listening socket. The daemon is parented directly to the `claude`
process (PID 1447 in the experiment).

What activates it: Claude Code spawns it on session start, and re-spawns
it on the next MCP tool call after a disconnect notice (verified below).

---

## Lifecycle Diagram

```
                     +---------+
                     |  COLD   |  no daemon process exists
                     +----+----+
                          |
              session start | next MCP tool call after disconnect
                          v
                     +---------+      banner returned on first
                     | RUNNING |---,  twin_session_status of this
                     +----+----+   |  process lifetime
                          |        |  (mcp_server.py:46-67, 493-495)
        SIGKILL / crash   |        |
                          v        |
                     +---------+   |
                     | KILLED  |   |
                     +----+----+   |
                          |        |
        Claude Code emits |        |
        disconnect notice |        |
                          v        |
                     +---------+   |
                     |  GONE   |   |  no auto-respawn timer observed;
                     +----+----+   |  daemon stays dead with zero
                          |        |  inbound MCP traffic (10s test)
        next MCP tool     |        |
        call from Claude  |        |
                          v        |
                     +---------+   |
                     |RESPAWN- |---'  fresh PID, fresh _engine,
                     |  ING    |     ephemeral state reset,
                     +---------+     SQLite/USD state preserved
```

State semantics:

- **In-memory state lost on respawn**: `_engine`, `_banner_shown`,
  `_hot_store`, `_injection_store`, `exchange_index`. References:
  `mcp_server.py:40, 45, 303, 304`, and the `process_exchange` index
  in the engine.
- **Persistent state survives**: SQLite (`data/twin.db`) and the v9
  observations DB (`data/observations.db`, fd 6 in lsof above).
  Verified: `observations_logged` advanced 117 → 134 → 142 → 143
  across four kill/respawn cycles in the experiment.

---

## Death Triggers

| Trigger | Observed behavior | Recovery path | Time-to-recovery |
| --- | --- | --- | --- |
| `SIGKILL` (`kill -9 <pid>`) | Process exits immediately; Claude Code MCP layer detects EOF on stdout pipe and emits a `system-reminder` declaring `harlo` disconnected | Next `mcp__harlo__*` tool call respawns the child | ~1–2 s wall clock for a fresh process to be importable + first call to return (cold imports + v9 engine init dominate) |
| Idle (no calls) | Daemon stays running. There is no `sock.settimeout()` on the MCP path, no idle-exit timer in `mcp_server.py`, no `while True` self-shutdown. The Rule-1 0-watt-idle path lives in the unused `daemon/main.py:84` and does **not** apply to stdio MCP. | n/a — daemon does not voluntarily exit | n/a |
| Claude Code session end | Claude Code closes stdin pipe; `server.run(transport="stdio")` returns; `atexit` handler at `mcp_server.py:91` calls `_engine.close()` | Next session start spawns fresh daemon | n/a |
| Python exception in tool body | Caught by per-tool `try/except` blocks (e.g. `mcp_server.py:259-260, 386-387`); returned as `{"status":"error", "error": ...}` JSON. Daemon stays alive. | None needed | n/a |

---

## Reconnect Triggers (Verified)

| Trigger | Next-tool-call result | Cited evidence |
| --- | --- | --- |
| `kill -9 <pid>` then immediate `mcp__harlo__twin_session_status` | Success. Response carries `banner` field (per `mcp_server.py:493-495`, `_consume_banner` returns the banner exactly once per process), `exchange_index: 1` (fresh `_engine`), and elevated `observations_logged` (state survived via disk). | Experiment T=1778347958.8: killed PID 2294. T=1778347970.7: pgrep showed PID 2347 (parent 1447 = Claude Code). MCP call returned banner + `observations_logged: 134`. |
| `kill -9` followed by 10 s of bash-only activity (no MCP calls) | Daemon stays dead. `pgrep -f harlo$` returns empty across 10 one-second polls. | Experiment T0=1778348015.66 through T0+10.68: empty `pgrep` at every sample. |
| `kill -9` followed by next MCP call after the 10 s silence | Success. Banner returned again, sessions_count grew to 9 (each respawn instantiates new SessionManager rows). | Experiment T=1778348035.7: killed PID 2545. T=1778348036.x: MCP call returned banner + `observations_logged: 143`. |

**Verified**: the next MCP tool call is the deterministic respawn trigger.

**Untested-because**: Claude Code may also have an internal keepalive/retry
that fires shortly after the disconnect notice; PIDs were observed appearing
during gap periods (e.g. PID 2560 between bash calls with no MCP traffic
from the diagnostician). The diagnostician could not isolate that path
without modifying Claude Code internals. From a smoke-test author's
perspective this does not matter: **issuing a tool call always works**, and
the worst case is one cold-start latency (~1–2 s).

**Untested-because**: a daemon that crashes mid-tool-call (vs. between
calls) was not exercised. The protocol-level behavior should be the same
(EOF on stdout → disconnect notice → next call respawns), but this is not
verified.

---

## Smoke-Test Recipe

To verify daemon liveness:

```bash
pgrep -af harlo
# Expect one Python process with parent PID == claude
```

To verify MCP reachability from inside a Claude Code session, call any
`mcp__harlo__*` tool and check `status: "ok"`. The cheapest is
`twin_session_status` (no DB writes):

```
mcp__harlo__twin_session_status()
```

To force a within-session reconnect for chaos testing:

```bash
P=$(pgrep -f "harlo$" | head -1)
kill -9 "$P"
# Then issue any mcp__harlo__* tool call from the Claude Code conversation.
# Banner field present in the response = fresh process confirmed.
```

To time a recovery cycle:

```bash
T0=$(date +%s.%N); kill -9 $(pgrep -f "harlo$" | head -1)
# Issue mcp__harlo__twin_session_status from the conversation
T1=$(date +%s.%N); echo "scale=3; $T1 - $T0" | bc
```

Cold-start cost dominates: `mcp.server.FastMCP` init, the lazy v9
`CognitiveEngine` build at `mcp_server.py:88-90` (USD stage load),
and the `_consume_banner` import path. Expect ~1–2 s on this hardware.

---

## Known Limitations

1. **No within-session passive recovery.** If the daemon is killed and no
   subsequent MCP tool call is issued, the `harlo` server stays
   disconnected for the rest of the silence. The `system-reminder`
   declaring disconnect is informational, not a heal. **Smoke tests must
   issue a tool call to confirm reconnect.**
2. **Banner is the only in-band liveness proof of a fresh process.** The
   `_banner_shown` flag at `mcp_server.py:46` is per-process. If a
   response includes `"banner": "..."`, the process was newly spawned
   since the last banner-bearing response. If the field is absent, the
   process is reused from a prior call. This is the only signal a
   smoke-test author has without sidecar `pgrep`.
3. **In-memory state is not preserved across respawn.** `exchange_index`
   resets to 1; `_engine` rebuilds; `_hot_store`/`_injection_store`
   reinitialize on first use. Tests that depend on monotonic
   `exchange_index` across a kill must be rewritten to be respawn-aware.
4. **No launchd/systemd integration on macOS for the MCP path.** The
   socket-activation code in `daemon/main.py` is unused by Claude Code's
   stdio transport. Don't expect 0-watt-idle behavior at the MCP layer;
   that property only applies to the legacy unix-socket daemon, which
   isn't installed on this machine (`ls ~/Library/LaunchAgents/` and
   `~/Library/LaunchDaemons/` returned no `harlo` entries).
5. **Multiple "ghost" sessions accumulate per respawn.** Each fresh
   process creates new SessionManager rows; the experiment grew the
   active-session count from 6 → 9 across kill/respawn cycles without
   manual cleanup. Smoke tests that assert on session count should reset
   `data/twin.db` between runs.
