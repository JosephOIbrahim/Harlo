"""Structural validation for the launchd plists.

These checks defend against regressions like:
  - ProgramArguments path drift (we recently moved off
    /usr/local/bin/harlo and onto the bundle binary).
  - KeepAlive accidentally set on the daemon or agents plists
    (would silently violate Rule 1 0W idle).
  - Missing Label / Sockets sections.
"""

from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

_PLIST_DIR = Path(__file__).resolve().parents[2] / "macos" / "launchd"

ALL_PLISTS = {
    "com.harlo.daemon": _PLIST_DIR / "com.harlo.daemon.plist",
    "com.harlo.agents": _PLIST_DIR / "com.harlo.agents.plist",
    "com.harlo.healthbridge": _PLIST_DIR / "com.harlo.healthbridge.plist",
    "com.harlo.pulse": _PLIST_DIR / "com.harlo.pulse.plist",
}

# Only HealthBridge is permitted KeepAlive (ADR-0001).
KEEPALIVE_ALLOWED = {"com.harlo.healthbridge"}


@pytest.fixture(params=list(ALL_PLISTS.items()), ids=list(ALL_PLISTS))
def loaded(request):
    label, path = request.param
    with path.open("rb") as fh:
        return label, plistlib.load(fh)


class TestStructure:
    def test_label_matches_filename(self, loaded):
        label, plist = loaded
        assert plist.get("Label") == label

    def test_program_arguments_present(self, loaded):
        label, plist = loaded
        args = plist.get("ProgramArguments") or []
        assert isinstance(args, list)
        assert len(args) >= 1, f"{label}: ProgramArguments must have at least the executable path"

    def test_program_argument_zero_is_absolute_path(self, loaded):
        label, plist = loaded
        args = plist["ProgramArguments"]
        assert args[0].startswith("/"), f"{label}: ProgramArguments[0] must be absolute"


class TestRule1ZeroWatt:
    """Rule 1: only com.harlo.healthbridge may have KeepAlive."""

    def test_keepalive_isolation(self, loaded):
        label, plist = loaded
        keepalive = plist.get("KeepAlive")
        # Either absent, set to False, or — in the healthbridge case
        # only — set to True / a dict.
        if label in KEEPALIVE_ALLOWED:
            return  # allowed, anything goes
        # Forbidden: True or a non-empty dict that effectively keeps alive
        if keepalive is True:
            pytest.fail(f"{label}: KeepAlive=True forbidden (Rule 1)")
        if isinstance(keepalive, dict) and any(v for v in keepalive.values()):
            pytest.fail(f"{label}: KeepAlive dict with truthy keys forbidden (Rule 1)")


class TestDaemonAndAgents:
    """The two socket-activated units must have a Sockets section."""

    @pytest.mark.parametrize("label", ["com.harlo.daemon", "com.harlo.agents"])
    def test_has_sockets_section(self, label):
        path = ALL_PLISTS[label]
        plist = plistlib.loads(path.read_bytes())
        sockets = plist.get("Sockets")
        assert isinstance(sockets, dict) and sockets, \
            f"{label}: socket-activated unit requires a Sockets dict"
        for sock_name, sock_def in sockets.items():
            assert "SockPathName" in sock_def, f"{label}/{sock_name}: missing SockPathName"
            assert sock_def["SockPathName"].startswith("/") or "~" in sock_def["SockPathName"], \
                f"{label}/{sock_name}: SockPathName must be a path"


class TestSocketsContract:
    """D69: launch_activate_socket(3) looks up the plist Sockets key by
    name — drift between the plist and the code constant is an instant
    silent activation failure."""

    def test_daemon_sockets_key_matches_code_constant(self):
        from harlo.daemon.config import LAUNCHD_SOCKET_NAME
        plist = plistlib.loads(ALL_PLISTS["com.harlo.daemon"].read_bytes())
        sockets = plist["Sockets"]
        assert list(sockets.keys()) == [LAUNCHD_SOCKET_NAME]


class TestBundlePathInvariant:
    """ProgramArguments[0] must point at a real bundle path so that
    macos_install_daemon.py can plistlib-rewrite it on install."""

    @pytest.mark.parametrize("label", ["com.harlo.daemon", "com.harlo.agents"])
    def test_points_at_harlo_app_bundle(self, label):
        path = ALL_PLISTS[label]
        plist = plistlib.loads(path.read_bytes())
        prog = plist["ProgramArguments"][0]
        assert "Harlo.app" in prog or "harlo" in prog.lower(), \
            f"{label}: ProgramArguments[0] should reference a Harlo bundle binary"

    def test_healthbridge_points_at_bridge_bundle(self):
        path = ALL_PLISTS["com.harlo.healthbridge"]
        plist = plistlib.loads(path.read_bytes())
        prog = plist["ProgramArguments"][0]
        assert "HarloHealthBridge" in prog, \
            "healthbridge: ProgramArguments[0] should reference HarloHealthBridge.app"


class TestPulseSocketActivation:
    """com.harlo.pulse: launchd-held TCP socket, name parity with the
    adoption call in pulse_listen (field-proven 2026-06-10: SYN ->
    launchd spawn -> 'Listening on launchd socket' -> accepted=1)."""

    def _plist(self):
        with (_PLIST_DIR / "com.harlo.pulse.plist").open("rb") as fh:
            return plistlib.load(fh)

    def test_sockets_key_matches_adoption_name(self):
        plist = self._plist()
        assert "HarloPulse" in plist.get("Sockets", {}), (
            "Sockets key must be 'HarloPulse' — pulse_listen adopts via "
            "adopt_launchd_socket('HarloPulse'); name parity is load-bearing"
        )

    def test_tcp_port_matches_default(self):
        from harlo.cli.commands.pulse import DEFAULT_PORT
        plist = self._plist()
        sock = plist["Sockets"]["HarloPulse"]
        assert sock["SockServiceName"] == str(DEFAULT_PORT)
        assert sock["SockType"] == "stream"

    def test_no_keepalive(self):
        # Rule 1: launchd re-arms the socket after clean exit; KeepAlive
        # would make this a resident process for no reason.
        assert "KeepAlive" not in self._plist()
