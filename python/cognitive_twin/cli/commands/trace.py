"""twin trace — Show details of a specific trace by ID."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def trace(id: str, as_json: bool):
    """Show details of a specific trace by ID."""
    result = send_command("trace", {"trace_id": id})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    trace_data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(trace_data, indent=2))
    else:
        _print_human(trace_data)


def _print_human(data: dict):
    """Print trace details in human-readable format."""
    if not data:
        click.echo("Trace not found.")
        return

    click.echo(f"Trace: {data.get('trace_id', '?')}")
    click.echo("-" * 50)
    click.echo(f"  Message:  {data.get('message', '')}")
    click.echo(f"  Domain:   {data.get('domain', '-')}")
    click.echo(f"  Strength: {data.get('strength', 0.0):.4f}")

    tags = data.get("tags", [])
    if tags:
        click.echo(f"  Tags:     {', '.join(tags)}")

    created = data.get("created_at", "")
    if created:
        click.echo(f"  Created:  {created}")

    click.echo("-" * 50)
