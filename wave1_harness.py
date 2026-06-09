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


def check_anchor_immunity():
    """USD-proof trial Cycle 4 / §F2 anchor structural-immunity follow-up:
    are anchor sections (CONSTITUTIONAL / SAFETY / CONSENT / KNOWLEDGE)
    structurally immune to injection on the live stage — bit-identical
    regardless of delta profile AND unmoved even by an adversarial delta
    that explicitly authors an opinion on an anchor path?

    Drives `anchor_demo` (which authors anchor + base layers + N delta
    profile layers including ONE adversarial + composed roots per profile
    with subLayerPaths=[anchor, delta_X, base]). Then from a cold pxr
    process, computes `hash_anchor_subtree(stage)` and
    `hash_nonanchor_subtree(stage)` for each composed profile and asserts:
      - All anchor_hashes == clean_anchor_hash (invariance, incl. adversarial)
      - Non-anchor hashes DIFFER across modulating profiles (delta non-vacuity)
      - The adversarial layer ACTUALLY authored its attack opinion (probe load-bearing)
      - The adversarial profile's composed anchor resolves to the CLEAN value,
        not the adversarial value (structural-vs-parametric — the attack
        was made but couldn't win)

    Per architect: testing only invariance without the adversarial probe is
    PARAMETRIC protection, not STRUCTURAL immunity. The adversarial probe is
    load-bearing — do not skip it. DO NOT elevate the anchor post-resolution
    or special-case it to force GREEN. Faking immunity is unacceptable.
    """
    c = MCPStdioClient(extra_env={REAL_USD_ENV: "1"})
    try:
        c.initialize()
        tools = c.list_tools()
        ai_tool = find_tool(tools, "anchor_demo")
        if not ai_tool:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"anchor_demo tool not exposed; tools = "
                    f"{[t.get('name') for t in tools]}")

        res = c.call_tool(ai_tool, {})
        if not isinstance(res, dict) or res.get("status") != "ok":
            err = (res.get("error") if isinstance(res, dict) else str(res))
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"anchor_demo error: {err}")

        paths = res.get("paths", {})
        clean_anchor_hash = res.get("clean_anchor_hash")
        profiles = res.get("profiles", [])
        adv_target = res.get("adversarial_attack_target")
        adv_attr = res.get("adversarial_attack_attr")
        adv_value = res.get("adversarial_attack_value")
        anchor_clean_values = res.get("anchor_clean_values", {})

        if not (clean_anchor_hash and profiles and adv_target):
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"anchor_demo response missing fields: {list(res.keys())}")

        try:
            from pxr import Sdf, Usd
        except ImportError:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    "pxr not importable in harness env")

        try:
            from harlo.usd_lite.anchor_demo import (
                hash_anchor_subtree, hash_nonanchor_subtree)
        except ImportError as e:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"hash_*_subtree not importable: {e}")

        # Per-profile cold-pxr hashes
        per_profile = {}
        for profile_name in profiles:
            composed_path = paths["composed_profiles"].get(profile_name)
            if not composed_path:
                return ("anchor immunity (§F2 follow-up)", "FAIL",
                        f"no composed path for profile {profile_name!r}")
            stage = Usd.Stage.Open(composed_path)
            if stage is None:
                return ("anchor immunity (§F2 follow-up)", "FAIL",
                        f"Stage.Open None for {composed_path}")
            per_profile[profile_name] = {
                "anchor_hash": hash_anchor_subtree(stage),
                "nonanchor_hash": hash_nonanchor_subtree(stage),
            }

        # Invariance: anchor_hash(profile) == clean_anchor_hash for ALL
        invariance_rows = []
        all_invariant = True
        for profile_name, hashes in per_profile.items():
            match = hashes["anchor_hash"] == clean_anchor_hash
            invariance_rows.append(
                f"{profile_name}={'OK' if match else 'MOVED'}")
            if not match:
                all_invariant = False

        # Non-vacuity: modulating-profile non-anchor hashes differ
        mod_profiles = [p for p in profiles if p != "adversarial"]
        nonanchor_set = {per_profile[p]["nonanchor_hash"] for p in mod_profiles}
        unique_nonanchor = len(nonanchor_set)
        deltas_real = (unique_nonanchor == len(mod_profiles))

        # Adversarial probe — verify attack was AUTHORED in the layer
        adv_layer = Sdf.Layer.FindOrOpen(paths["deltas"]["adversarial"])
        if adv_layer is None:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    "adversarial layer could not be opened")
        adv_attack_spec = adv_layer.GetAttributeAtPath(
            f"{adv_target}.{adv_attr}")
        attack_authored = (adv_attack_spec is not None
                           and adv_attack_spec.default == adv_value)

        # Adversarial probe — verify attack FAILED (composed view = clean)
        adv_composed = Usd.Stage.Open(paths["composed_profiles"]["adversarial"])
        anchor_name = adv_target.split("/")[-1]
        adv_resolved = (adv_composed.GetPrimAtPath(adv_target)
                        .GetAttribute(adv_attr).Get())
        adv_expected_clean = anchor_clean_values.get(anchor_name)
        attack_failed = (adv_resolved == adv_expected_clean)

        detail = (
            f"clean={clean_anchor_hash[:12]}.. · "
            f"invariance[{', '.join(invariance_rows)}] · "
            f"deltas_real={deltas_real}(uniq nonanchor={unique_nonanchor}/{len(mod_profiles)}) · "
            f"adv_authored={attack_authored} · "
            f"adv_resolved={adv_resolved!r}(clean={adv_expected_clean!r}, "
            f"attack={adv_value!r}) · attack_failed={attack_failed}"
        )

        if not attack_authored:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"adversarial attack NOT authored — test is vacuous: {detail}")
        if not deltas_real:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"modulating deltas are vacuous — non-anchor invariant: {detail}")
        if not all_invariant:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"FALSIFIED: anchor MOVED across profiles — structural "
                    f"immunity FALSE: {detail}")
        if not attack_failed:
            return ("anchor immunity (§F2 follow-up)", "FAIL",
                    f"FALSIFIED: adversarial attack SUCCEEDED — anchor resolved "
                    f"to {adv_resolved!r}: {detail}")
        return ("anchor immunity (§F2 follow-up)", "PASS", detail)
    except Exception as e:
        return ("anchor immunity (§F2 follow-up)", "FAIL",
                f"exception: {type(e).__name__}: {e}")
    finally:
        c.close()


def check_structural_lossless():
    """USD-proof trial P4 / §F2 thesis test: reconstruct_clean() as
    flatten-to-base recovers the clean baseline BIT-IDENTICALLY from a
    composed stage that has both base and delta sublayers.

    Drives `lossless_demo` (which authors clean + delta sublayers and a
    composed root, plus a clean-only composed root for the reference
    clean_hash). Then from a cold pxr process: confirms delta is non-empty
    (composed view ≠ clean value), confirms identity-at-zero (no-delta view
    == clean), runs reconstruct_clean(composed_with_delta) → recovered
    string, SHA256s it, compares bit-identically against the server-side
    clean_hash (which uses the SAME canonical serialization path).

    Per architect: §F2 firing is SUCCESS (loop exit), not failure. DO NOT
    massage the comparison (loosen the hash, fall back to float-tol,
    post-patch the recovered layer). Faking the lossless guarantee is the
    one unacceptable outcome.
    """
    c = MCPStdioClient(extra_env={REAL_USD_ENV: "1"})
    try:
        c.initialize()
        tools = c.list_tools()
        ll_tool = find_tool(tools, "lossless_demo")
        if not ll_tool:
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"lossless_demo tool not exposed; tools = "
                    f"{[t.get('name') for t in tools]}")

        res = c.call_tool(ll_tool, {})
        if not isinstance(res, dict) or res.get("status") != "ok":
            err = (res.get("error") if isinstance(res, dict) else str(res))
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"lossless_demo error: {err}")

        paths = res.get("paths", {})
        clean_hash_server = res.get("clean_hash")
        clean_value = res.get("clean_value")
        delta_modulated_value = res.get("delta_modulated_value")
        delta_magnitude = res.get("delta_magnitude")
        signal_attr = res.get("signal_attr")
        signal_prim = res.get("signal_prim")
        composed_delta_path = paths.get("composed_with_delta")
        composed_clean_path = paths.get("composed_clean_only")

        if not (composed_delta_path and composed_clean_path and clean_hash_server):
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"lossless_demo response missing fields: {list(res.keys())}")

        try:
            from pxr import Sdf, Usd
        except ImportError:
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    "pxr not importable in harness env — install usd-core")

        # Sanity 1: delta is non-empty (composed view != clean value).
        composed_stage = Usd.Stage.Open(composed_delta_path)
        if composed_stage is None:
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"Stage.Open returned None for {composed_delta_path}")
        composed_view_cold = (composed_stage.GetPrimAtPath(signal_prim)
                              .GetAttribute(signal_attr).Get())
        if composed_view_cold == clean_value:
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"delta is empty (composed_view={composed_view_cold!r} "
                    f"== clean={clean_value!r}) — test is vacuous")

        # Sanity 2: identity at zero — no-delta composed view == clean.
        clean_only_stage = Usd.Stage.Open(composed_clean_path)
        identity_view = (clean_only_stage.GetPrimAtPath(signal_prim)
                         .GetAttribute(signal_attr).Get())
        identity_ok = (identity_view == clean_value)

        # The real test: reconstruct_clean on composed-with-delta should
        # produce the same canonical string as the reference clean.
        import hashlib
        try:
            from harlo.usd_lite.lossless_demo import reconstruct_clean
        except ImportError as e:
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"reconstruct_clean not importable: {e}")

        recovered_string = reconstruct_clean(composed_delta_path)
        recovered_hash = hashlib.sha256(recovered_string.encode()).hexdigest()
        match = (recovered_hash == clean_hash_server)
        fidelity = 1.0 if match else 0.0

        # Semantic sanity: parse the recovered string and confirm the
        # signal attribute holds the CLEAN value, not the delta-modulated.
        recovered_layer = Sdf.Layer.CreateAnonymous(".usda")
        recovered_layer.ImportFromString(recovered_string)
        sig_spec = recovered_layer.GetAttributeAtPath(
            f"{signal_prim}.{signal_attr}")
        recovered_signal_value = sig_spec.default if sig_spec else None
        semantic_ok = (recovered_signal_value == clean_value)

        if match and identity_ok and semantic_ok:
            detail = (
                f"clean={clean_hash_server[:16]}.. recovered={recovered_hash[:16]}.. "
                f"fidelity={fidelity} · delta={delta_magnitude} "
                f"(composed={composed_view_cold}, clean={clean_value}) · "
                f"identity_at_zero=OK · semantic_signal={recovered_signal_value}"
            )
            return ("structural lossless (P4 / §F2 test)", "PASS", detail)

        if not match:
            return ("structural lossless (P4 / §F2 test)", "FAIL",
                    f"§F2 FIRED: clean_hash={clean_hash_server} != "
                    f"recovered_hash={recovered_hash} (fidelity={fidelity}) · "
                    f"delta_magnitude={delta_magnitude} · "
                    f"composed_view={composed_view_cold} · "
                    f"recovered_signal_value={recovered_signal_value}")

        problems = []
        if not identity_ok:
            problems.append(f"identity_at_zero failed: composed_clean_only "
                            f"resolved {identity_view!r} != clean {clean_value!r}")
        if not semantic_ok:
            problems.append(f"semantic check failed: recovered signal "
                            f"{recovered_signal_value!r} != clean {clean_value!r}")
        return ("structural lossless (P4 / §F2 test)", "FAIL",
                "; ".join(problems))
    except Exception as e:
        return ("structural lossless (P4 / §F2 test)", "FAIL",
                f"exception: {type(e).__name__}: {e}")
    finally:
        c.close()


def check_native_composition():
    """USD-proof trial P3 / §F1 thesis test: pxr's native composition resolves
    cognitive priority L > V > S on the live `real_usd` stage.

    Drives `compose_demo` (which authors LOCAL + VARIANT + SPECIALIZE arcs on
    three sibling prims), then opens the demo stage from this harness process
    via cold `pxr.Usd.Stage.Open` and asserts pxr's RESOLVED `attr.Get()`
    matches the cognitively-correct winner at each tier.

    Per architect: §F1 firing is SUCCESS (honest falsification), not failure.
    DO NOT bolt on overrides to force GREEN — the verifier reports pxr's
    actual resolution; faking is the unacceptable outcome.
    """
    c = MCPStdioClient(extra_env={REAL_USD_ENV: "1"})
    try:
        c.initialize()
        tools = c.list_tools()
        compose_tool = find_tool(tools, "compose_demo")
        if not compose_tool:
            return ("native composition (P3 / §F1 test)", "FAIL",
                    f"compose_demo tool not exposed; tools = "
                    f"{[t.get('name') for t in tools]}")

        res = c.call_tool(compose_tool, {})
        if not isinstance(res, dict) or res.get("status") != "ok":
            err = (res.get("error") if isinstance(res, dict) else str(res))
            return ("native composition (P3 / §F1 test)", "FAIL",
                    f"compose_demo error: {err}")

        path = res.get("path")
        scenarios = res.get("scenarios", [])
        attr_name = res.get("attribute")

        if not path or not os.path.exists(path):
            return ("native composition (P3 / §F1 test)", "FAIL",
                    f"demo stage path missing: {path!r}")

        try:
            from pxr import Usd
        except ImportError:
            return ("native composition (P3 / §F1 test)", "FAIL",
                    "pxr not importable in harness env — install usd-core")

        stage = Usd.Stage.Open(path)
        if stage is None:
            return ("native composition (P3 / §F1 test)", "FAIL",
                    f"Usd.Stage.Open returned None for {path}")

        results = []
        all_pass = True
        f1_fired = False
        for scenario in scenarios:
            sc_path = scenario["path"]
            expected = scenario["expected_value"]
            expected_arc = scenario["expected_winner"]

            prim = stage.GetPrimAtPath(sc_path)
            if not prim.IsValid():
                results.append(
                    f"{sc_path}: PRIM_MISSING (expected {expected_arc}="
                    f"{expected!r})")
                all_pass = False
                continue

            attr = prim.GetAttribute(attr_name)
            if not attr or not attr.IsValid():
                results.append(
                    f"{sc_path}: ATTR_MISSING (expected {expected_arc}="
                    f"{expected!r})")
                all_pass = False
                continue

            actual = attr.Get()
            if actual == expected:
                results.append(
                    f"{sc_path.split('/')[-1]}: {expected_arc}={expected!r} OK")
            else:
                # §F1 surface: pxr's resolution doesn't match cognitive priority.
                results.append(
                    f"{sc_path.split('/')[-1]}: §F1-FIRE expected "
                    f"{expected_arc}={expected!r}, pxr resolved {actual!r}")
                all_pass = False
                f1_fired = True

        detail = " | ".join(results)
        if all_pass:
            return ("native composition (P3 / §F1 test)", "PASS",
                    f"path={path} · {detail}")
        if f1_fired:
            return ("native composition (P3 / §F1 test)", "FAIL",
                    f"§F1 FIRED on live pxr resolution · {detail}")
        return ("native composition (P3 / §F1 test)", "FAIL", detail)
    except Exception as e:
        return ("native composition (P3 / §F1 test)", "FAIL",
                f"exception: {type(e).__name__}: {e}")
    finally:
        c.close()


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
               check_populated_hierarchy(), check_native_composition(),
               check_structural_lossless(), check_anchor_immunity()]

    print("\nScoreboard")
    print("-" * 66)
    for name, status, detail in results:
        print(f"  [{status:^4}] {name}")
        print(f"         {detail}")
    print("-" * 66)

    live = next(r for r in results if r[0].startswith("live USD"))
    p1 = next((r for r in results if r[0].startswith("populated hierarchy")), None)
    p3 = next((r for r in results if r[0].startswith("native composition")), None)
    p4 = next((r for r in results if r[0].startswith("structural lossless")), None)
    p4b = next((r for r in results if r[0].startswith("anchor immunity")), None)

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

    if p3 is not None:
        print("\nP3 verdict (USD-proof trial — §F1 USD-native-priority thesis):")
        if p3[1] == "PASS":
            print("  PASS  pxr resolves L > V > S on the live stage.")
            print("        §F1 status: thesis CONFIRMED for this attribute.")
        elif "§F1 FIRED" in p3[2]:
            print("  FAIL  §F1 has FIRED — honest falsification (per rulebook,")
            print("        this is a successful loop exit, not a code bug).")
            print(f"        Evidence: {p3[2]}")
        else:
            print("  FAIL  P3 not yet green (not a §F1 firing). Scope:")
            print(f"        {p3[2]}")

    if p4 is not None:
        print("\nP4 verdict (USD-proof trial — §F2 structural lossless thesis):")
        if p4[1] == "PASS":
            print("  PASS  reconstruct_clean recovers clean BIT-IDENTICALLY.")
            print("        §F2 status: structural lossless CONFIRMED.")
        elif "§F2 FIRED" in p4[2]:
            print("  FAIL  §F2 has FIRED — honest falsification (lossless must")
            print("        stay computational, structural recovery insufficient).")
            print(f"        Evidence: {p4[2]}")
        else:
            print("  FAIL  P4 not yet green (not a §F2 firing). Scope:")
            print(f"        {p4[2]}")

    if p4b is not None:
        print("\nP4b verdict (USD-proof trial — §F2 anchor structural immunity):")
        if p4b[1] == "PASS":
            print("  PASS  anchors structurally immune — invariant across delta")
            print("        profiles, adversarial attack authored but FAILED.")
        elif "FALSIFIED" in p4b[2]:
            print("  FAIL  FALSIFIED — anchors are NOT structurally immune.")
            print("        Anchor moved (or adversarial succeeded). Lossless")
            print("        structural-only claim is false; revisit reframe.")
            print(f"        Evidence: {p4b[2]}")
        else:
            print("  FAIL  P4b not yet green (not a falsification firing). Scope:")
            print(f"        {p4b[2]}")
    print()
    live_ok = live[1] == "PASS"
    p1_ok = p1 is not None and p1[1] == "PASS"
    p3_ok = p3 is not None and p3[1] == "PASS"
    p4_ok = p4 is not None and p4[1] == "PASS"
    p4b_ok = p4b is not None and p4b[1] == "PASS"
    return 0 if (live_ok and p1_ok and p3_ok and p4_ok and p4b_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
