"""twin undo — Undo a previous action."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("action_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def undo(action_id: str, as_json: bool):
    """Undo a previous action by ACTION_ID."""
    result = send_command("undo", {"action_id": action_id})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(data, indent=2))
    else:
        state = data.get("state", "undone")
        click.echo(f"Action {action_id}: {state}")
