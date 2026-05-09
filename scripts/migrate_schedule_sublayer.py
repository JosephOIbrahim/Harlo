"""CLI: migrate /schedule/ off harlo.usda onto a dedicated schedule.usda sublayer.

Idempotent. Safe to re-run. Prints a JSON status to stdout.

Usage:
    python scripts/migrate_schedule_sublayer.py [STAGE_DIR]

If STAGE_DIR is omitted, defaults to ./data/stages.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.schedule_migrate import migrate_inline

    if len(sys.argv) > 2:
        print("usage: migrate_schedule_sublayer.py [STAGE_DIR]", file=sys.stderr)
        return 2

    stage_dir = sys.argv[1] if len(sys.argv) == 2 else os.path.join("data", "stages")
    if not os.path.isdir(stage_dir):
        print(json.dumps({"status": "no_stage_dir", "stage_dir": stage_dir}))
        return 1

    result = migrate_inline(stage_dir)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
