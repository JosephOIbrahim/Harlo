"""twin audit — Show audit trail for a composition stage."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def audit(id: str, as_json: bool):
    """Show audit trail for a stage or specific entry ID."""
    result = send_command("audit", {"id": id})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    audit_data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(audit_data, indent=2))
    else:
        _print_human(audit_data, id)


def _print_human(data: dict, audit_id: str):
    """Print audit trail in human-readable format."""
    entries = data.get("entries", [])

    click.echo(f"Audit trail: {audit_id}")
    click.echo("-" * 50)

    if not entries:
        click.echo("  No audit entries found.")
        click.echo("-" * 50)
        return

    for i, entry in enumerate(entries, 1):
        ts = entry.get("timestamp", "?")
        action = entry.get("action", "?")
        stage_id = entry.get("stage_id", "?")
        detail = entry.get("detail", "")

        click.echo(f"  {i}. [{ts}] {action}")
        click.echo(f"     Stage: {stage_id}")
        if detail:
            click.echo(f"     Detail: {detail}")
        click.echo()

    click.echo("-" * 50)
    click.echo(f"  {len(entries)} audit entries")
