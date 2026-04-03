"""twin stuck — Show all UNPROVABLE/DEFERRED verification results."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def stuck(as_json: bool):
    """Show all UNPROVABLE and DEFERRED verification results."""
    result = send_command("stuck", {})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    items = result.get("result", {}).get("items", [])

    if as_json:
        click.echo(json.dumps(result.get("result", {}), indent=2))
    else:
        _print_human(items)


def _print_human(items: list):
    """Print stuck verification items in human-readable format."""
    if not items:
        click.echo("No stuck verifications.")
        return

    click.echo(f"Stuck verifications ({len(items)}):")
    click.echo("-" * 50)

    for i, item in enumerate(items, 1):
        stage_id = item.get("stage_id", "unknown")
        state = item.get("state", "UNKNOWN")
        reason = item.get("reason", "")
        what_would_help = item.get("what_would_help", "")
        partial_progress = item.get("partial_progress", "")

        click.echo(f"  {i}. [{state}] stage {stage_id}")
        if reason:
            click.echo(f"     Reason: {reason}")
        if what_would_help:
            click.echo(f"     What would help: {what_would_help}")
        if partial_progress:
            click.echo(f"     Partial progress: {partial_progress}")
        click.echo()

    click.echo("-" * 50)
    click.echo(f"  {len(items)} stuck items")
