#!/usr/bin/env python3
"""
Wave 1 trio harness  ·  proves the first step (live USD twin) works.

FIRST PRINCIPLES
  The irreducible question is: does flipping USE_REAL_USD=1 move the twin from
  mock -> live?  To answer it WITHOUT guessing Harlo's internals, this harness
  drives the same MCP stdio interface already verified live (status + recall):
    - discovers tool names via tools/list   (no hardcoded names)
    - reads stage_type out of the status payload at v9.engine.stage_type
    - asserts the value changes mock -> NOT-mock  (no guessing the live string)
  It spawns its own throwaway Harlo server processes, so it never touches your
  Claude Desktop daemon. Honest by construction: if live USD fails to load, you
  get the real error, not a green checkmark.

RUN
  /Users/rustybeard/Code/Harlo/.venv312/bin/python wave1_harness.py
  (stdlib only — any python3 works. Server logs/banner stream to your terminal.)
"""

import json
import os
import select
import subprocess
import sys
import time

# ---- config (edit only if your path / flag differ) -------------------------
HARLO_BIN     = "/Users/rustybeard/Code/Harlo/.venv312/bin/harlo"
REAL_USD_ENV  = "USE_REAL_USD"      # the env flag that flips mock -> live
SPAWN_TIMEOUT = 90                  # seconds to wait for a reply (USD load can be slow)
PROTOCOL_VER  = "2025-06-18"        # MCP version we offer; server negotiates its own
# ----------------------------------------------------------------------------


class MCPError(Exception):
    pass


class MCPStdioClient:
    """Minimal MCP stdio client: spawn server, JSON-RPC over newline-delimited pipes."""

    def __init__(self, extra_env=None):
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        self.proc = subprocess.Popen(
            [HARLO_BIN],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,            # inherit -> server logs/banner go to your terminal
            env=env,
        )
        self._id = 0
        self._buf = b""

    def _send(self, msg):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        self.proc.stdin.flush()

    def _read_message(self, deadline):
        while True:
            nl = self._buf.find(b"\n")
            if nl != -1:
                line = self._buf[:nl].strip()
                self._buf = self._buf[nl + 1:]
                if not line:
                    continue
                try:
                    return json.loads(line.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue  # skip non-JSON noise on stdout
            timeout = deadline - time.time()
            if timeout <= 0:
                raise MCPError("timeout waiting for server response")
            if self.proc.poll() is not None:
                raise MCPError(f"server exited (code {self.proc.returncode}) before responding")
            r, _, _ = select.select([self.proc.stdout], [], [], min(timeout, 1.0))
            if r:
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if chunk == b"":
                    raise MCPError("server closed stdout")
                self._buf += chunk

    def _request(self, method, params=None, timeout=SPAWN_TIMEOUT):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        deadline = time.time() + timeout
        while True:
            msg = self._read_message(deadline)
            if msg.get("id") == rid:
                if "error" in msg:
                    raise MCPError(f"{method} -> {msg['error']}")
                return msg.get("result", {})
            # ignore notifications / mismatched ids

    def _notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self):
        self._request("initialize", {
            "protocolVersion": PROTOCOL_VER,
            "capabilities": {},
            "clientInfo": {"name": "wave1-harness", "version": "0.1"},
        })
        self._notify("notifications/initialized")

    def list_tools(self):
        return self._request("tools/list").get("tools", [])

    def call_tool(self, name, arguments=None):
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        content = result.get("content")
        if isinstance(content, list) and content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return {"_raw": content[0]["text"]}
        return result

    def close(self):
        for fn in (lambda: self.proc.stdin.close(),
                   lambda: self.proc.terminate(),
                   lambda: self.proc.wait(timeout=5)):
            try:
                fn()
            except Exception:
                pass
        if self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass


def find_tool(tools, needle):
    for t in tools:
        if needle.lower() in t.get("name", "").lower():
            return t["name"]
    return None


def dig(d, *path):
    """Walk nested dicts; fall back to a recursive search for the final key."""
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            cur = None
            break
    if cur is not None:
        return cur
    target = path[-1]
    stack = [d]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if target in node:
                return node[target]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


def get_stage_type(extra_env=None):
    c = MCPStdioClient(extra_env=extra_env)
    try:
        c.initialize()
        tools = c.list_tools()
        status_tool = find_tool(tools, "status")
        if not status_tool:
            raise MCPError(f"no status tool; tools = {[t.get('name') for t in tools]}")
        status = c.call_tool(status_tool, {})
        return dig(status, "v9", "engine", "stage_type"), status
    finally:
        c.close()


# ---- the three checks ------------------------------------------------------

def check_recall():
    c = MCPStdioClient()
    try:
        c.initialize()
        recall_tool = find_tool(c.list_tools(), "recall")
        if not recall_tool:
            return ("recall", "NA", "no recall tool exposed")
        res = c.call_tool(recall_tool, {"query": "wave1 harness probe", "depth": "normal"})
        if isinstance(res, dict) and res.get("status") == "error":
            return ("recall", "FAIL", res.get("error", "unknown error"))
        return ("recall", "PASS", "recall returned without error")
    except MCPError as e:
        return ("recall", "FAIL", str(e))
    finally:
        c.close()


def check_spike():
    return ("#2 App Intent spike", "NA",
            "separate Swift build the harness can't run; status: not run")


def check_populated_hierarchy():
    """USD-proof trial P1 verifier: stage traversal returns a populated hierarchy.

    Drives minimal real state (entity via the existing `store` tool; session
    auto-created inside `persist_stage`), calls `persist_stage` to write the
    current brain to disk, then opens the persisted .usda from this harness
    process and asserts session + entity prim presence. Decision tier is
    deferred per architect amendment 2 — no minimal-flow MotorPrim production
    exists in the v9 engine.
    """
    c = MCPStdioClient(extra_env={REAL_USD_ENV: "1"})
    try:
        c.initialize()
        tools = c.list_tools()

        persist_tool = find_tool(tools, "persist_stage")
        store_tool = find_tool(tools, "store")
        status_tool = find_tool(tools, "status")

        if not persist_tool:
            return ("populated hierarchy (P1)", "FAIL",
                    f"persist_stage tool not exposed; tools = "
                    f"{[t.get('name') for t in tools]}")

        # Drive minimal state: status triggers engine init, store creates >=1 hot_trace.
        if status_tool:
            c.call_tool(status_tool, {})
        if store_tool:
            store_res = c.call_tool(store_tool,
                                    {"message": "wave1 trial probe entity",
                                     "tags": ["wave1-trial"]})
            if isinstance(store_res, dict) and store_res.get("status") == "error":
                return ("populated hierarchy (P1)", "FAIL",
                        f"store failed: {store_res.get('error')}")

        persist_res = c.call_tool(persist_tool, {})
        if not isinstance(persist_res, dict) or persist_res.get("status") != "ok":
            err = (persist_res.get("error")
                   if isinstance(persist_res, dict) else str(persist_res))
            return ("populated hierarchy (P1)", "FAIL", f"persist_stage error: {err}")

        path = persist_res.get("path")
        tier_counts = persist_res.get("tier_counts", {})
        decision_deferred = persist_res.get("decision_deferred", False)
        decision_reason = persist_res.get("decision_deferred_reason", "")

        if not path or not os.path.exists(path):
            return ("populated hierarchy (P1)", "FAIL", f"stage path missing: {path!r}")

        # Open + traverse from this harness process — proves a real .usda file,
        # not a JSON the server made up.
        try:
            from pxr import Usd
        except ImportError:
            return ("populated hierarchy (P1)", "FAIL",
                    "pxr not importable in harness env — install usd-core in .venv312")

        stage = Usd.Stage.Open(path)
        if stage is None:
            return ("populated hierarchy (P1)", "FAIL",
                    f"Usd.Stage.Open returned None for {path}")

        brain = stage.GetPrimAtPath("/Brain")
        if not brain.IsValid():
            return ("populated hierarchy (P1)", "FAIL",
                    "/Brain prim missing in persisted stage")

        session_prim = stage.GetPrimAtPath("/Brain/Session")
        traces_root = stage.GetPrimAtPath("/Brain/Association/Traces")
        traces = list(traces_root.GetChildren()) if traces_root.IsValid() else []

        session_id = ""
        if session_prim.IsValid():
            attr = session_prim.GetAttribute("current_session_id")
            if attr and attr.IsValid():
                session_id = attr.Get() or ""

        session_ok = session_prim.IsValid() and bool(session_id)
        entity_ok = len(traces) >= 1

        decision_str = (f"deferred ({decision_reason})"
                        if decision_deferred else "?")
        detail = (
            f"path={path} · "
            f"session={'PASS' if session_ok else 'FAIL'}(id={session_id!r}, "
            f"tier_count={tier_counts.get('session', 0)}) · "
            f"entity={'PASS' if entity_ok else 'FAIL'}"
            f"({len(traces)} TracePrim, tier_count={tier_counts.get('entity', 0)}) · "
            f"decision={decision_str}"
        )

        if session_ok and entity_ok:
            return ("populated hierarchy (P1)", "PASS", detail)
        return ("populated hierarchy (P1)", "FAIL", detail)
    except Exception as e:
        return ("populated hierarchy (P1)", "FAIL",
                f"exception: {type(e).__name__}: {e}")
    finally:
        c.close()


def check_live_usd():
    try:
        base_st, _ = get_stage_type(extra_env=None)
    except MCPError as e:
        return ("live USD (FIRST STEP)", "FAIL", f"baseline status failed: {e}")
    try:
        live_st, _ = get_stage_type(extra_env={REAL_USD_ENV: "1"})
    except MCPError as e:
        return ("live USD (FIRST STEP)", "FAIL",
                f"baseline stage_type={base_st!r}; flip FAILED: {e}")
    detail = f"stage_type {base_st!r} -> {live_st!r}"
    if live_st is None:
        return ("live USD (FIRST STEP)", "FAIL", detail + " (no stage_type in flipped status)")
    if str(live_st).lower() == "mock":
        return ("live USD (FIRST STEP)", "FAIL",
                detail + f" ({REAL_USD_ENV}=1 did not flip off mock)")
    return ("live USD (FIRST STEP)", "PASS", detail + " — flipped off mock")


def main():
    print("=" * 66)
    print(" Wave 1 trio harness  ·  proving the first step (live USD)")
    print("=" * 66)
    if not os.path.exists(HARLO_BIN):
        print(f"\n  ABORT: HARLO_BIN not found -> {HARLO_BIN}")
        print("  Edit the config block at the top of this file.\n")
        return 2

    results = [check_recall(), check_spike(), check_live_usd(),
               check_populated_hierarchy()]

    print("\nScoreboard")
    print("-" * 66)
    for name, status, detail in results:
        print(f"  [{status:^4}] {name}")
        print(f"         {detail}")
    print("-" * 66)

    live = next(r for r in results if r[0].startswith("live USD"))
    p1 = next((r for r in results if r[0].startswith("populated hierarchy")), None)

    print("\nFirst-step verdict:")
    if live[1] == "PASS":
        print("  PASS  live USD twin flips mock -> live. The first step works.")
    else:
        print("  FAIL  live USD did NOT flip. This scopes the surgery:")
        print(f"        {live[2]}")

    if p1 is not None:
        print("\nP1 verdict (USD-proof trial — populated hierarchy):")
        if p1[1] == "PASS":
            print("  PASS  session + entity tiers populated on live real_usd stage.")
            print("        Decision tier status reported in the scoreboard detail.")
        else:
            print("  FAIL  P1 not yet green. Scope:")
            print(f"        {p1[2]}")
    print()
    live_ok = live[1] == "PASS"
    p1_ok = p1 is not None and p1[1] == "PASS"
    return 0 if (live_ok and p1_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
