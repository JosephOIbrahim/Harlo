"""twin consent — Manage motor consent levels."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("action", type=click.Choice(["level-1", "level-2", "revoke", "show"]))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def consent(action: str, as_json: bool):
    """Manage motor consent: level-1, level-2, revoke, or show."""
    result = send_command("consent", {"action": action})

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
        level = data.get("level", "unknown")
        if action == "show":
            click.echo(f"Current consent level: {level}")
        elif action == "revoke":
            click.echo("Motor consent revoked.")
        else:
            click.echo(f"Consent set to: {action}")
