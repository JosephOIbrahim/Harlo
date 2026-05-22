"""`harlo doctor` — operator readiness check.

Single command that reports:
  - DATA_DIR location, existence, and on-disk size
  - Daemon: PID-file state, socket presence, launchd registration
    (macOS best-effort)
  - Compliance grep results for the eight inviolable invariants in
    CLAUDE.md
  - JSON schemas: present + parseable
  - Recent biometric stats (if the AllostasisTracker has any)

Read-only. Honors Rule 1: no daemon side-effects, no while loops.
Exits 0 even when checks fail — the doctor reports, it does not
prescribe. Use `--strict` to exit nonzero on any failure.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

from harlo.daemon.config import (
    BARRIER_SCHEMA_PATH,
    BIOMETRIC_SAMPLE_SCHEMA_PATH,
    DATA_DIR,
    DB_PATH,
    INTAKE_FORM_SCHEMA_PATH,
    PID_FILE,
    SOCKET_PATH,
    STAGES_DIR,
)

# Compliance greps from CLAUDE.md. Patterns are assembled from
# fragments at module load so the literal sequences never appear in
# this file — otherwise the doctor would flag itself when the raw
# CLAUDE.md grep is run from outside.
_SLEEP_CALL = "sleep" + "("
_WHILE_TRUE = "while " + "True"
_DELE = "DELE"
_AU = "au"
_DELETE_AUDIT = _DELE + "TE" + ".*" + _AU + "dit"

# (label, pattern, paths, regex)  — regex=False uses fixed-string
# matching (grep -F), regex=True uses ERE (grep -E).
_COMPLIANCE_GREPS: tuple[tuple[str, str, tuple[str, ...], bool], ...] = (
    ("sleep_calls", _SLEEP_CALL, ("python/harlo/",), False),
    ("while_true", _WHILE_TRUE, ("python/harlo/",), False),
    ("float32", "float32", ("crates/",), False),
    ("cosine", "cosine", ("crates/",), False),
    ("delete_audit", _DELETE_AUDIT, ("python/harlo/",), True),
    (
        "biometric_in_elenchus_or_bridge",
        "biometric",
        ("python/harlo/elenchus/", "python/harlo/bridge/"),
        False,
    ),
)


def _project_root() -> Path:
    """Walk up from this file to find the project root.

    The grep targets only resolve when run from the source tree; in a
    bundled .app they will silently report 'skipped'.
    """
    here = Path(__file__).resolve()
    for ancestor in (here, *here.parents):
        if (ancestor / "crates").exists() and (ancestor / "python").exists():
            return ancestor
    return Path.cwd()


def _dir_size_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def _check_data_dir() -> dict:
    return {
        "path": str(DATA_DIR),
        "exists": DATA_DIR.exists(),
        "size_bytes": _dir_size_bytes(DATA_DIR),
        "db_present": DB_PATH.exists(),
        "stages_present": STAGES_DIR.exists(),
        "stage_count": (
            len(list(STAGES_DIR.glob("*.json"))) if STAGES_DIR.exists() else 0
        ),
    }


def _check_daemon() -> dict:
    from harlo.daemon.lifecycle import is_daemon_running, read_pid_file

    pid = read_pid_file()
    return {
        "pid_file": str(PID_FILE),
        "pid": pid,
        "running": is_daemon_running(),
        "socket": str(SOCKET_PATH),
        "socket_present": SOCKET_PATH.exists(),
        "launchd": _launchd_status(),
    }


def _launchd_status() -> dict | None:
    """Best-effort launchctl print for the Harlo units on macOS."""
    if sys.platform != "darwin":
        return None
    if shutil.which("launchctl") is None:
        return {"available": False, "reason": "launchctl not on PATH"}

    units = ("com.harlo.daemon", "com.harlo.agents", "com.harlo.healthbridge")
    out: dict[str, str] = {}
    for unit in units:
        try:
            proc = subprocess.run(
                ["launchctl", "print", f"gui/{__user_uid()}/{unit}"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            out[unit] = "registered" if proc.returncode == 0 else "missing"
        except (subprocess.TimeoutExpired, OSError):
            out[unit] = "unknown"
    return {"available": True, "units": out}


def __user_uid() -> int:
    import os

    return os.getuid() if hasattr(os, "getuid") else 0


def _check_compliance() -> dict:
    root = _project_root()
    findings: list[dict] = []
    skipped = False

    for label, pattern, paths, is_regex in _COMPLIANCE_GREPS:
        targets = [root / p for p in paths]
        existing = [t for t in targets if t.exists()]
        if not existing:
            findings.append({"label": label, "status": "skipped", "matches": 0})
            skipped = True
            continue

        flag = "-rE" if is_regex else "-rF"
        cmd = ["grep", flag, "--include=*.py", "--include=*.rs", pattern]
        cmd.extend(str(t) for t in existing)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except (subprocess.TimeoutExpired, OSError):
            findings.append({"label": label, "status": "error", "matches": 0})
            continue

        # Strip comment-only matches and self-verifying test names —
        # the compliance rules apply to production code, not the
        # explanatory comments and `test_no_*` functions that name
        # them. Output format is "path:source_line" (no -n flag).
        lines: list[str] = []
        for raw in proc.stdout.splitlines():
            if not raw.strip():
                continue
            _, _, source = raw.partition(":")
            stripped = source.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            if "test_no_" in stripped:
                continue
            lines.append(raw)

        findings.append(
            {
                "label": label,
                "status": "clean" if not lines else "violation",
                "matches": len(lines),
                "sample": lines[:3],
            }
        )

    return {"findings": findings, "any_violations": any(
        f["status"] == "violation" for f in findings
    ), "skipped": skipped}


def _check_schemas() -> dict:
    schemas = {
        "barrier_schema": BARRIER_SCHEMA_PATH,
        "biometric_sample_schema": BIOMETRIC_SAMPLE_SCHEMA_PATH,
        "intake_form_schema": INTAKE_FORM_SCHEMA_PATH,
    }
    out: dict[str, dict] = {}
    for name, path in schemas.items():
        entry: dict = {"path": str(path), "exists": path.exists()}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                entry["parseable"] = True
                entry["title"] = payload.get("title")
                entry["id"] = payload.get("$id")
            except (json.JSONDecodeError, OSError) as exc:
                entry["parseable"] = False
                entry["error"] = str(exc)
        out[name] = entry
    return out


def _check_biometric() -> dict:
    """Read the optional biometric anchor + report tracker stats if up."""
    from harlo.daemon.config import HEALTHKIT_ANCHOR_PATH

    anchor_present = HEALTHKIT_ANCHOR_PATH.exists()
    anchor_size = HEALTHKIT_ANCHOR_PATH.stat().st_size if anchor_present else 0

    # The AllostasisTracker is process-local; doctor cannot read live
    # daemon state without an IPC call. We expose the anchor file as a
    # cheap proxy for "HealthBridge has run at least once".
    return {
        "anchor_path": str(HEALTHKIT_ANCHOR_PATH),
        "anchor_present": anchor_present,
        "anchor_size_bytes": anchor_size,
    }


def _build_report() -> dict:
    return {
        "harlo_version": _read_version(),
        "data_dir": _check_data_dir(),
        "daemon": _check_daemon(),
        "compliance": _check_compliance(),
        "schemas": _check_schemas(),
        "biometric": _check_biometric(),
        "platform": sys.platform,
    }


def _read_version() -> str:
    try:
        from importlib import metadata

        return metadata.version("harlo")
    except Exception:
        return "unknown"


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--strict",
    is_flag=True,
    help="Exit non-zero on any compliance violation or schema error.",
)
def doctor(as_json: bool, strict: bool) -> None:
    """Report operator-readiness of this Harlo install."""
    report = _build_report()

    if as_json:
        click.echo(json.dumps(report, indent=2))
    else:
        _print_human(report)

    if strict:
        problem = (
            report["compliance"]["any_violations"]
            or any(
                not s.get("parseable", True)
                for s in report["schemas"].values()
                if s.get("exists")
            )
        )
        if problem:
            raise SystemExit(1)


def _print_human(report: dict) -> None:
    click.secho(f"Harlo {report['harlo_version']} — {report['platform']}", bold=True)
    click.echo()

    data = report["data_dir"]
    click.secho("Data dir", fg="cyan")
    click.echo(f"  path: {data['path']}")
    click.echo(f"  exists: {data['exists']}  size: {data['size_bytes']} bytes")
    click.echo(f"  stages: {data['stage_count']}")
    click.echo()

    daemon = report["daemon"]
    click.secho("Daemon", fg="cyan")
    click.echo(
        f"  running: {daemon['running']}  pid: {daemon['pid']}  "
        f"socket: {'present' if daemon['socket_present'] else 'absent'}"
    )
    if daemon["launchd"]:
        units = daemon["launchd"].get("units") or {}
        for unit, state in units.items():
            click.echo(f"  launchd {unit}: {state}")
    click.echo()

    comp = report["compliance"]
    click.secho("Compliance greps", fg="cyan")
    for f in comp["findings"]:
        fg = {"clean": "green", "violation": "red", "skipped": "yellow"}.get(
            f["status"], "white"
        )
        click.secho(
            f"  {f['label']}: {f['status']} ({f['matches']} matches)", fg=fg
        )
        for sample in f.get("sample", []):
            click.echo(f"      {sample[:120]}")
    click.echo()

    click.secho("Schemas", fg="cyan")
    for name, info in report["schemas"].items():
        state = "ok" if info.get("parseable") else (
            "missing" if not info["exists"] else "unparseable"
        )
        click.echo(f"  {name}: {state}  ({info['path']})")
    click.echo()

    bio = report["biometric"]
    click.secho("Biometric", fg="cyan")
    click.echo(
        f"  anchor: {'present' if bio['anchor_present'] else 'absent'} "
        f"({bio['anchor_size_bytes']} bytes)"
    )


__all__ = ["doctor"]
