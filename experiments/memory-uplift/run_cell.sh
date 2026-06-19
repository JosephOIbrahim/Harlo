#!/usr/bin/env bash
# run_cell.sh <cell> <snapshot-dir> — orchestrate one experiment cell.
#
#   launchd check -> stop daemon -> restore snapshot -> start daemon with
#   the cell's env (cold: daemon stays DOWN) -> capture pre.json ->
#   "READY" -> operator runs the subject session -> ENTER -> capture
#   post.json -> write-leak check.
#
# Write-leak detector: row count of observation_buffer in observations.db
# (read-only sqlite query — independent of the status JSON schema).
#   warm-mem  : count MUST be unchanged (OBSERVATION_LOGGING=0) — hard fail.
#   cold      : daemon is down; unchanged expected — warn only.
#   warm-full : growth expected — reported, not asserted.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PY="$REPO/.venv312/bin/python"
DATA_ROOT="${HARLO_DATA_DIR:-$HOME/Library/Application Support/Harlo}"

refuse() { echo "REFUSED: $*" >&2; exit 2; }
die()    { echo "FAILED: $*" >&2; exit 1; }

CELL="${1:-}"; SNAP="${2:-}"
[[ -n "$CELL" && -n "$SNAP" ]] || die "usage: run_cell.sh <cold|warm-mem|warm-full> <snapshot-dir>"
ENV_FILE="$HERE/cells/$CELL.env"
[[ -f "$ENV_FILE" ]] || die "unknown cell '$CELL' (no $ENV_FILE)"
[[ -d "$SNAP" ]] || die "no such snapshot dir: $SNAP"

RUN_DIR="$HERE/runs/$CELL"
if [[ -d "$RUN_DIR" ]] && [[ -n "$(ls -A "$RUN_DIR" 2>/dev/null)" ]]; then
    die "runs/$CELL already has results — move it aside before re-running (no silent overwrites)"
fi
mkdir -p "$RUN_DIR"

# ---- launchd unload check --------------------------------------------
for unit in com.harlo.daemon com.harlo.agents com.harlo.pulse; do
    if launchctl print "gui/$(id -u)/$unit" >/dev/null 2>&1; then
        refuse "launchd unit $unit is loaded — the experiment window requires all Harlo units unloaded: launchctl bootout gui/\$(id -u)/$unit"
    fi
done

# ---- stop any running daemon (tolerate not-running) -------------------
"$PY" "$REPO/scripts/stop_daemon.py" >/dev/null 2>&1 || true
if [[ -f "$DATA_ROOT/twind.pid" ]]; then
    pid="$(cat "$DATA_ROOT/twind.pid")"
    if kill -0 "$pid" 2>/dev/null; then
        die "daemon still alive after stop_daemon.py (pid $pid)"
    fi
fi

# ---- restore the cell's starting state --------------------------------
"$HERE/restore.sh" "$SNAP"

obs_count() {
    sqlite3 "file:$DATA_ROOT/observations.db?mode=ro" \
        "SELECT COUNT(*) FROM observation_buffer;" 2>/dev/null || echo "ERR"
}

extract_json() {
    # Tolerate a boot banner before the JSON: take from the first '{',
    # raw_decode so trailing noise can't break the parse.
    "$PY" -c '
import json, sys
s = sys.stdin.read()
i = s.find("{")
if i < 0:
    sys.exit("no JSON object found in status output")
obj, _ = json.JSONDecoder().raw_decode(s[i:])
print(json.dumps(obj, indent=2))
'
}

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }

DAEMON_PID=""
cleanup() {
    if [[ -n "$DAEMON_PID" ]] && kill -0 "$DAEMON_PID" 2>/dev/null; then
        kill "$DAEMON_PID" 2>/dev/null || true
        wait "$DAEMON_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

OBS_PRE="$(obs_count)"

if [[ "$CELL" == "cold" ]]; then
    echo "[cold] daemon stays DOWN — confirm the harlo MCP server is unmounted in the subject client."
    printf '{"cell":"cold","daemon":"down","observation_rows":%s,"captured_at":"%s"}\n' \
        "$OBS_PRE" "$(stamp)" > "$RUN_DIR/pre.json"
else
    set -a
    # shellcheck source=/dev/null
    . "$ENV_FILE"
    set +a
    "$PY" "$REPO/scripts/start_daemon.py" > "$RUN_DIR/daemon.log" 2>&1 &
    DAEMON_PID=$!
    echo "$DAEMON_PID" > "$RUN_DIR/daemon.pid"
    for _ in $(seq 1 50); do
        [[ -S "$DATA_ROOT/twind.sock" ]] && break
        sleep 0.2
    done
    [[ -S "$DATA_ROOT/twind.sock" ]] || die "daemon socket never appeared (see $RUN_DIR/daemon.log)"
    "$PY" -m harlo.cli.main status --json 2>"$RUN_DIR/status_pre.stderr" \
        | extract_json > "$RUN_DIR/pre.json" \
        || die "could not capture pre.json (see $RUN_DIR/status_pre.stderr)"
fi
echo "$OBS_PRE" > "$RUN_DIR/obs_count_pre"

echo
echo "READY: run subject session now"
echo "  cell=$CELL  snapshot=$SNAP  obs_rows_pre=$OBS_PRE"
read -r -p "Press ENTER when the subject session is complete... "

if [[ "$CELL" == "cold" ]]; then
    printf '{"cell":"cold","daemon":"down","observation_rows":%s,"captured_at":"%s"}\n' \
        "$(obs_count)" "$(stamp)" > "$RUN_DIR/post.json"
else
    "$PY" -m harlo.cli.main status --json 2>"$RUN_DIR/status_post.stderr" \
        | extract_json > "$RUN_DIR/post.json" \
        || die "could not capture post.json (see $RUN_DIR/status_post.stderr)"
fi
OBS_POST="$(obs_count)"
echo "$OBS_POST" > "$RUN_DIR/obs_count_post"

# ---- write-leak detector ----------------------------------------------
case "$CELL" in
    warm-mem)
        if [[ "$OBS_PRE" != "$OBS_POST" ]]; then
            echo "WRITE LEAK: observation_buffer grew $OBS_PRE -> $OBS_POST with OBSERVATION_LOGGING=0" >&2
            exit 4
        fi
        echo "leak check PASS: observation rows unchanged ($OBS_PRE)"
        ;;
    cold)
        if [[ "$OBS_PRE" != "$OBS_POST" ]]; then
            echo "WARNING: observation rows changed $OBS_PRE -> $OBS_POST with the daemon DOWN — something else wrote the store" >&2
        else
            echo "leak check PASS: observation rows unchanged ($OBS_PRE)"
        fi
        ;;
    warm-full)
        echo "observation rows: $OBS_PRE -> $OBS_POST (growth expected in warm-full)"
        ;;
esac

echo "CELL COMPLETE: results in $RUN_DIR"
