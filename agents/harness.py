"""MOE agent harness — socket-activated router.

Honors Rule 1: no `while True`, no `sleep()`. The harness is invoked
by launchd when a producer connects to the agents socket, drains the
queue, persists outputs, and exits.

This is a scaffold. Wiring to the actual Claude Agent SDK is left as
a follow-up (the role files in `agents/roles/` define the prompts;
the runner currently only validates descriptors and writes a stub
output).
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from harlo.daemon.config import (
    AGENTS_OUTPUTS_DIR,
    AGENTS_QUEUE_DIR,
    ensure_data_dirs,
)


SUPPORTED_ROLES = {
    "architect",
    "scout",
    "os_engineer",
    "intake_engineer",
    "health_bridge",
    "ux_designer",
}


@dataclass(frozen=True)
class TaskDescriptor:
    id: str
    role: str
    title: str
    constraints: tuple[str, ...]
    context_files: tuple[str, ...]
    acceptance: tuple[str, ...]
    source_path: Path


def _load_descriptor(path: Path) -> TaskDescriptor:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    role = raw.get("role")
    if role not in SUPPORTED_ROLES:
        raise ValueError(
            f"{path.name}: role {role!r} not in {sorted(SUPPORTED_ROLES)}"
        )
    return TaskDescriptor(
        id=str(raw["id"]),
        role=role,
        title=str(raw.get("title", "")),
        constraints=tuple(raw.get("constraints") or ()),
        context_files=tuple(raw.get("context_files") or ()),
        acceptance=tuple(raw.get("acceptance") or ()),
        source_path=path,
    )


def _output_dir(task_id: str) -> Path:
    d = AGENTS_OUTPUTS_DIR / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _record_dispatch(task: TaskDescriptor) -> Path:
    out_dir = _output_dir(task.id)
    record = {
        "task": {k: v for k, v in asdict(task).items() if k != "source_path"},
        "dispatched_at": datetime.now(tz=timezone.utc).isoformat(),
        "status": "pending",
        "note": (
            "Scaffold: harness wrote this record without invoking the "
            "Claude Agent SDK. Wire claude-agent-sdk to execute."
        ),
    }
    out_file = out_dir / "dispatch.json"
    out_file.write_text(
        json.dumps(record, indent=2, default=str), encoding="utf-8"
    )
    return out_file


def _drain_queue() -> list[Path]:
    """Process every YAML file under agents/queue, return paths of
    successfully recorded outputs. Source descriptors are NOT deleted
    here — that is the producer's responsibility on confirmation.
    """
    outputs: list[Path] = []
    if not AGENTS_QUEUE_DIR.exists():
        return outputs
    for entry in sorted(AGENTS_QUEUE_DIR.glob("*.yaml")):
        try:
            task = _load_descriptor(entry)
        except (yaml.YAMLError, ValueError, KeyError) as exc:
            sys.stderr.write(f"harness: skip {entry.name}: {exc}\n")
            continue
        outputs.append(_record_dispatch(task))
    return outputs


def _accept_one_connection() -> None:
    """When launched via launchd socket activation we inherit FD 3 as
    a listening socket. Accept one connection (to release the
    activator), then drain. Idle exit follows immediately.
    """
    listen_fds = int(os.environ.get("LISTEN_FDS", "0"))
    if listen_fds < 1:
        return
    sock = socket.socket(fileno=3)
    try:
        sock.settimeout(0.1)
        try:
            conn, _ = sock.accept()
            conn.close()
        except (socket.timeout, OSError):
            pass
    finally:
        sock.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harlo-agents")
    parser.add_argument(
        "--socket-activated",
        action="store_true",
        help="Accept one connection from the launchd socket before draining.",
    )
    args = parser.parse_args(argv)

    ensure_data_dirs()
    if args.socket_activated:
        _accept_one_connection()
    written = _drain_queue()
    sys.stdout.write(
        json.dumps(
            {"drained": [str(p) for p in written], "count": len(written)},
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
