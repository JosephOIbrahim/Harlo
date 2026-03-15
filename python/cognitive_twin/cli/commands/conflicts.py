"""twin conflicts — Show conflicts in a composition stage."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--stage", required=True, help="Stage ID to check for conflicts")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def conflicts(stage: str, as_json: bool):
    """Show conflicts in a composition stage."""
    result = send_command("conflicts", {"stage_id": stage})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    conflicts_data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(conflicts_data, indent=2))
    else:
        _print_human(conflicts_data, stage)


def _print_human(data: dict, stage_id: str):
    """Print conflicts in human-readable format."""
    conflict_list = data.get("conflicts", [])
    layer_count = data.get("layer_count", 0)

    click.echo(f"Conflicts: stage {stage_id} ({layer_count} layers)")
    click.echo("-" * 50)

    if not conflict_list:
        click.echo("  No conflicts detected.")
        click.echo("-" * 50)
        return

    for i, conflict in enumerate(conflict_list, 1):
        attr = conflict.get("attribute", "?")
        values = conflict.get("values", [])
        winning = conflict.get("winning_value", "?")
        winning_arc = conflict.get("winning_arc", "?")

        click.echo(f"  {i}. Attribute: {attr}")
        click.echo(f"     Contested values: {len(values)}")
        for v in values:
            src = v.get("arc_type", "?")
            val = v.get("value", "?")
            click.echo(f"       [{src}] {val}")
        click.echo(f"     Winner: {winning} (via {winning_arc})")
        click.echo()

    click.echo("-" * 50)
    click.echo(f"  {len(conflict_list)} conflict(s) found")
