"""twin inquire — Surface pending inquiries."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option(
    "--depth",
    type=click.Choice(["light", "standard", "deep"]),
    default="standard",
    help="Inquiry depth",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def inquire(depth: str, as_json: bool):
    """Surface pending inquiries at the specified depth."""
    result = send_command("inquire", {"depth": depth})

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
        _print_human(data, depth)


def _print_human(data: dict, depth: str):
    """Print inquiries in human-readable format."""
    items = data.get("inquiries", [])

    if not items:
        click.echo("No pending inquiries.")
        return

    click.echo(f"Pending inquiries (depth={depth}):")
    click.echo("-" * 50)

    for i, item in enumerate(items, 1):
        question = item.get("question", str(item))
        priority = item.get("priority", "")
        tag = f" [{priority}]" if priority else ""
        click.echo(f"  {i}. {question}{tag}")

    click.echo("-" * 50)
    click.echo(f"  {len(items)} inquiries")
