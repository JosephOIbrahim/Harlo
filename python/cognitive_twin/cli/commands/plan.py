"""twin plan — Generate an action plan."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("intent")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def plan(intent: str, as_json: bool):
    """Generate an action plan for the given INTENT."""
    result = send_command("plan", {"intent": intent})

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
        _print_human(data, intent)


def _print_human(data: dict, intent: str):
    """Print plan in human-readable format."""
    plan_id = data.get("plan_id", "unknown")
    steps = data.get("steps", [])

    click.echo(f"Plan: {intent}")
    click.echo(f"  ID: {plan_id}")
    click.echo("-" * 50)

    for i, step in enumerate(steps, 1):
        desc = step.get("description", str(step))
        click.echo(f"  {i}. {desc}")

    click.echo("-" * 50)
    click.echo(f"  {len(steps)} steps")
