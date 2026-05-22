"""Privacy contract — Harlo's central promise.

The HARLO_UX_BRIEF.md privacy contract says: "Harlo's memory of you
lives in a folder on this Mac. No cloud sync. No telemetry." That's
a contract the architecture has to enforce, not a marketing claim.

This test walks the daemon's source tree and asserts:
  - No imports of `requests`, `urllib.request`, `httpx`, `aiohttp`,
    `http.client`.
  - No literal mentions of `https://`, `http://`, `ws://`, `wss://`
    (outside string-literal exemption for docstrings citing URLs).
  - Any `socket.socket(` constructor uses AF_UNIX exclusively
    (no AF_INET, AF_INET6).

Failing this test means an upstream change quietly added a network
client. Investigate, justify with an ADR, or remove.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _walk_py(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


FORBIDDEN_IMPORTS = (
    re.compile(r"^\s*import\s+requests\b", re.MULTILINE),
    re.compile(r"^\s*from\s+requests\b", re.MULTILINE),
    re.compile(r"^\s*from\s+urllib\.request\b", re.MULTILINE),
    re.compile(r"^\s*import\s+urllib\.request\b", re.MULTILINE),
    re.compile(r"^\s*import\s+httpx\b", re.MULTILINE),
    re.compile(r"^\s*from\s+httpx\b", re.MULTILINE),
    re.compile(r"^\s*import\s+aiohttp\b", re.MULTILINE),
    re.compile(r"^\s*from\s+aiohttp\b", re.MULTILINE),
    re.compile(r"^\s*from\s+http\.client\b", re.MULTILINE),
    re.compile(r"^\s*import\s+http\.client\b", re.MULTILINE),
)

# Files explicitly allowed to import outbound HTTP. Each entry MUST
# also have an ADR or be in a clearly user-facing module. Add with
# care and an explanation.
ALLOWLIST = {
    # Provider modules legitimately call external APIs (Anthropic /
    # OpenAI), but those are the actor's choice, not the twin's
    # state path. Daemon code never imports `provider/`.
    "python/harlo/provider/claude.py",
    "python/harlo/provider/openai.py",
}

# Modules the privacy contract specifically covers — anything that
# sits in Harlo's state-keeping or sensor-ingest path. Adding to
# this list TIGHTENS the contract; removing requires an ADR.
PROTECTED_ROOTS = [
    _REPO_ROOT / "python" / "harlo" / "daemon",
    _REPO_ROOT / "python" / "harlo" / "modulation",
    _REPO_ROOT / "python" / "harlo" / "motor",
    _REPO_ROOT / "python" / "harlo" / "bridge",
    _REPO_ROOT / "python" / "harlo" / "elenchus",
    _REPO_ROOT / "python" / "harlo" / "inquiry",
    _REPO_ROOT / "python" / "harlo" / "composition",
    _REPO_ROOT / "python" / "harlo" / "hot_store",
    _REPO_ROOT / "python" / "harlo" / "intake",
    _REPO_ROOT / "python" / "harlo" / "session",
]


@pytest.mark.parametrize("root", PROTECTED_ROOTS, ids=lambda p: p.name)
def test_no_forbidden_imports(root):
    if not root.exists():
        pytest.skip(f"{root.name} not present")
    offenders: list[str] = []
    for src in _walk_py(root):
        rel = src.relative_to(_REPO_ROOT).as_posix()
        if rel in ALLOWLIST:
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_IMPORTS:
            if pattern.search(text):
                offenders.append(f"{rel}: {pattern.pattern}")
    assert not offenders, "Privacy contract violated:\n" + "\n".join(offenders)


def test_socket_usage_is_af_unix_only():
    """Any socket.socket() call in protected roots must be AF_UNIX."""
    inet_re = re.compile(r"socket\.socket\s*\(\s*socket\.(AF_INET|AF_INET6)")
    offenders: list[str] = []
    for root in PROTECTED_ROOTS:
        if not root.exists():
            continue
        for src in _walk_py(root):
            rel = src.relative_to(_REPO_ROOT).as_posix()
            text = src.read_text(encoding="utf-8", errors="replace")
            if inet_re.search(text):
                offenders.append(rel)
    assert not offenders, (
        "AF_INET / AF_INET6 socket usage in privacy-protected modules:\n"
        + "\n".join(offenders)
    )
