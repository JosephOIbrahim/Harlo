"""twin profile — Show current modulation profile."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def profile(as_json: bool):
    """Show the current modulation profile."""
    result = send_command("profile", {})

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
        _print_human(data)


def _print_human(data: dict):
    """Print modulation profile in human-readable format."""
    click.echo("Modulation Profile")
    click.echo("-" * 50)

    for key, value in sorted(data.items()):
        click.echo(f"  {key}: {value}")

    click.echo("-" * 50)
