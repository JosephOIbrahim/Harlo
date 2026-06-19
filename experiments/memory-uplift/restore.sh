#!/usr/bin/env bash
# restore.sh <snapshot-dir> — restore a snapshot.sh capture onto DATA_ROOT.
#
# Order of operations matters:
#   1. Verify the snapshot against its own manifest (refuse a bit-rotted
#      snapshot before touching anything live).
#   2. Remove the live DB set INCLUDING -wal/-shm sidecars even when the
#      snapshot has none — a stale WAL replayed against a restored main
#      file is silent corruption.
#   3. Copy the manifest's file set back.
#   4. Re-verify the RESTORED files against the same manifest (paths are
#      relative, so the manifest validates either root). Fail loudly.
#
# Same guards as snapshot.sh. Extra .usda files on the live side that are
# not in the snapshot are left in place (this restores state, it does not
# garbage-collect).
set -euo pipefail

DATA_ROOT="${HARLO_DATA_DIR:-$HOME/Library/Application Support/Harlo}"

refuse() { echo "REFUSED: $*" >&2; exit 2; }
die()    { echo "FAILED: $*" >&2; exit 1; }

SNAP="${1:-}"
[[ -n "$SNAP" ]] || die "usage: restore.sh <snapshot-dir>"
[[ -d "$SNAP" ]] || die "no such snapshot dir: $SNAP"
# Absolutize: step 4 re-verifies after `cd "$DATA_ROOT"`, where a relative
# snapshot path would no longer resolve.
SNAP="$(cd "$SNAP" && pwd)"
[[ -f "$SNAP/manifest.sha256" ]] || die "snapshot has no manifest.sha256: $SNAP"

# ---- guards (identical to snapshot.sh) -------------------------------
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

if [[ -f "$DATA_ROOT/twin.db" ]]; then
    holders="$(lsof -t -- "$DATA_ROOT/twin.db" 2>/dev/null || true)"
    if [[ -n "$holders" ]]; then
        refuse "twin.db is held open by pid(s): $holders. Quit the holder first."
    fi
fi

# ---- 1. snapshot integrity -------------------------------------------
( cd "$SNAP" && shasum -a 256 -c manifest.sha256 --status ) \
    || die "snapshot integrity check FAILED — $SNAP does not match its own manifest"

# ---- 2. clear live DB set (sidecars unconditionally) ------------------
rm -f "$DATA_ROOT/twin.db" "$DATA_ROOT/twin.db-wal" "$DATA_ROOT/twin.db-shm" \
      "$DATA_ROOT/observations.db"

# ---- 3. copy back ----------------------------------------------------
while IFS= read -r rel; do
    mkdir -p "$DATA_ROOT/$(dirname "$rel")"
    cp "$SNAP/$rel" "$DATA_ROOT/$rel"
done < <(cd "$SNAP" && find . -type f ! -name manifest.sha256 | sed 's|^\./||')

# ---- 4. verify restored files ----------------------------------------
( cd "$DATA_ROOT" && shasum -a 256 -c "$SNAP/manifest.sha256" --status ) \
    || die "RESTORE HASH MISMATCH — live store may be inconsistent; re-run restore from a good snapshot"

echo "RESTORE OK: $SNAP -> $DATA_ROOT"
