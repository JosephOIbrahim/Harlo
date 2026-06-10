#!/usr/bin/env bash
# snapshot.sh — cold snapshot of the live Harlo store.
#
# Captures: twin.db (+ -wal/-shm sidecars if present), observations.db,
# stages/**/*.usda — into snapshots/<timestamp>/ with a SHA256 manifest
# (shasum -c compatible, paths relative to both the snapshot dir and
# DATA_ROOT, so the same manifest verifies both sides).
#
# Guards (all hard-refuse): launchd units loaded, daemon PID alive,
# daemon socket present, ANY process holding twin.db open (catches the
# Claude Desktop MCP server, which is neither a daemon nor a launchd unit).
set -euo pipefail

DATA_ROOT="${HARLO_DATA_DIR:-$HOME/Library/Application Support/Harlo}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
SNAP="$HERE/snapshots/$STAMP"

refuse() { echo "REFUSED: $*" >&2; exit 2; }

# ---- guards ----------------------------------------------------------
for unit in com.harlo.daemon com.harlo.agents com.harlo.pulse; do
    if launchctl print "gui/$(id -u)/$unit" >/dev/null 2>&1; then
        refuse "launchd unit $unit is loaded. Unload first: launchctl bootout gui/\$(id -u)/$unit"
    fi
done

PID_FILE="$DATA_ROOT/twind.pid"
if [[ -f "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE")"
    if kill -0 "$pid" 2>/dev/null; then
        refuse "daemon alive (pid $pid from twind.pid). Stop it: python scripts/stop_daemon.py"
    fi
fi

if [[ -S "$DATA_ROOT/twind.sock" ]]; then
    refuse "daemon socket present ($DATA_ROOT/twind.sock). Stop the daemon or remove the stale socket."
fi

holders="$(lsof -t -- "$DATA_ROOT/twin.db" 2>/dev/null || true)"
if [[ -n "$holders" ]]; then
    refuse "twin.db is held open by pid(s): $holders — likely the Claude Desktop MCP server. Quit the holder first."
fi

# ---- capture ---------------------------------------------------------
[[ -f "$DATA_ROOT/twin.db" ]] || refuse "no twin.db at $DATA_ROOT"
[[ -f "$DATA_ROOT/observations.db" ]] || refuse "no observations.db at $DATA_ROOT"

mkdir -p "$SNAP"
cp "$DATA_ROOT/twin.db" "$SNAP/"
for side in twin.db-wal twin.db-shm; do
    if [[ -f "$DATA_ROOT/$side" ]]; then
        cp "$DATA_ROOT/$side" "$SNAP/"
    fi
done
cp "$DATA_ROOT/observations.db" "$SNAP/"

if [[ -d "$DATA_ROOT/stages" ]]; then
    rsync -a --include='*/' --include='*.usda' --exclude='*' \
        "$DATA_ROOT/stages/" "$SNAP/stages/"
fi

# ---- manifest --------------------------------------------------------
(
    cd "$SNAP"
    find . -type f ! -name manifest.sha256 | sed 's|^\./||' | sort \
        | xargs shasum -a 256 > manifest.sha256
)

echo "SNAPSHOT OK: $SNAP"
sed 's/^/  /' "$SNAP/manifest.sha256"
