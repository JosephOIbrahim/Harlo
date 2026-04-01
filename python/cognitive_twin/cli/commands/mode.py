"""twin mode — Switch operational mode."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("target", type=click.Choice(["utility", "partner"]))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def mode(target: str, as_json: bool):
    """Switch operational mode to utility or partner."""
    result = send_command("mode", {"mode": target})

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
        click.echo(f"Mode switched to: {data.get('mode', target)}")
