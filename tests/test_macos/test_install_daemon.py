"""D70/D71 — installer tilde expansion + bundle-aware plist discovery.

D70: launchd never expands '~'; a literal-~ SockPathName means the
socket can never bind where clients look. The repo plists keep '~' as
the template marker and the installer rewrites them at install time.

D71: inside a py2app bundle the plists live in Contents/Resources/
launchd/ (and the installer in Contents/Resources/scripts/), so the
dev-tree-only PLIST_DIR constant raised FileNotFoundError there.

The script is not a package — imported via importlib from scripts/.
These tests live beside test_launchd_plists.py (not tests/test_daemon/)
because they test scripts/ + plists, not the daemon package.
"""

from __future__ import annotations

import copy
import importlib.util
import plistlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "scripts" / "macos_install_daemon.py"
_DAEMON_PLIST = REPO_ROOT / "macos" / "launchd" / "com.harlo.daemon.plist"


def _load_script():
    spec = importlib.util.spec_from_file_location("macos_install_daemon", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


installer = _load_script()


def _flat_strings(value):
    """Yield every string anywhere in a plist-shaped structure."""
    if isinstance(value, dict):
        for v in value.values():
            yield from _flat_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _flat_strings(v)
    elif isinstance(value, str):
        yield value


class TestExpandTildes:
    def test_expand_tildes_rewrites_all_path_keys(self):
        """The REAL daemon plist, with an injected home: SockPathName,
        both log paths, and HARLO_DATA_DIR all rewritten; zero '~' left."""
        plist = plistlib.loads(_DAEMON_PLIST.read_bytes())
        out = installer._expand_tildes(plist, home=Path("/Users/testuser"))

        assert out["Sockets"]["HarloCommand"]["SockPathName"] == (
            "/Users/testuser/Library/Application Support/Harlo/twind.sock"
        )
        assert out["StandardOutPath"].startswith("/Users/testuser/Library/Logs/")
        assert out["StandardErrorPath"].startswith("/Users/testuser/Library/Logs/")
        assert out["EnvironmentVariables"]["HARLO_DATA_DIR"] == (
            "/Users/testuser/Library/Application Support/Harlo"
        )
        assert all("~" not in s for s in _flat_strings(out))

    def test_expand_tildes_leaves_absolute_paths_alone(self):
        """Absolute paths pass through value-identical; input not mutated."""
        plist = {
            "StandardOutPath": "/var/log/harlo.out",
            "StandardErrorPath": "/var/log/harlo.err",
            "EnvironmentVariables": {"HARLO_DATA_DIR": "/srv/harlo"},
            "Sockets": {
                "HarloCommand": {
                    "SockPathName": "/srv/harlo/twind.sock",
                    "SockPathMode": 384,
                }
            },
        }
        original = copy.deepcopy(plist)
        out = installer._expand_tildes(plist, home=Path("/Users/testuser"))
        assert out == original
        assert plist == original  # input dict not mutated


class TestFindPlistDir:
    def test_find_plist_dir_dev_tree(self):
        """Pure path logic + exists check — runs anywhere."""
        assert installer._find_plist_dir() == REPO_ROOT / "macos" / "launchd"

    def test_find_plist_dir_bundle_layout(self, tmp_path, monkeypatch):
        """D71 pin: Resources/scripts/../launchd is discovered when the
        dev tree is absent (the py2app bundle layout)."""
        scripts_dir = tmp_path / "Resources" / "scripts"
        launchd_dir = tmp_path / "Resources" / "launchd"
        scripts_dir.mkdir(parents=True)
        launchd_dir.mkdir(parents=True)
        (launchd_dir / "com.harlo.daemon.plist").write_bytes(
            plistlib.dumps({"Label": "com.harlo.daemon"})
        )

        mod = _load_script()  # fresh instance — don't pollute the shared one
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path / "no-dev-tree")
        monkeypatch.setattr(
            mod, "__file__", str(scripts_dir / "macos_install_daemon.py")
        )
        assert mod._find_plist_dir() == launchd_dir
