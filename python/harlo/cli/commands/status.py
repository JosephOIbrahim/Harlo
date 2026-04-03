"""twin status — Show system status."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(as_json: bool):
    """Show Harlo system status."""
    result = send_command("status", {})

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Harlo v{result.get('version', '?')}")
        click.echo(f"  State: {result.get('state', 'unknown')}")
        click.echo(f"  Status: {result.get('status', 'unknown')}")
