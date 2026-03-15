"""twin deferred — List or flush deferred verifications."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--flush", is_flag=True, help="Run all deferred verifications now")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def deferred(flush: bool, as_json: bool):
    """List deferred verifications, or flush them with --flush."""
    result = send_command("deferred", {"flush": flush})

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
        if flush:
            _print_flush_result(data)
        else:
            _print_human(data)


def _print_human(data: dict):
    """Print deferred verifications in human-readable format."""
    items = data.get("items", [])

    if not items:
        click.echo("No deferred verifications.")
        return

    click.echo(f"Deferred verifications ({len(items)}):")
    click.echo("-" * 50)

    for i, item in enumerate(items, 1):
        stage_id = item.get("stage_id", "unknown")
        reason = item.get("reason", "")
        deferred_at = item.get("deferred_at", "")

        click.echo(f"  {i}. stage {stage_id}")
        if reason:
            click.echo(f"     Reason: {reason}")
        if deferred_at:
            click.echo(f"     Deferred at: {deferred_at}")
        click.echo()

    click.echo("-" * 50)
    click.echo(f"  {len(items)} deferred items")


def _print_flush_result(data: dict):
    """Print flush results in human-readable format."""
    flushed = data.get("flushed", 0)
    results = data.get("results", [])

    click.echo(f"Flushed {flushed} deferred verifications.")
    click.echo("-" * 50)

    for i, res in enumerate(results, 1):
        stage_id = res.get("stage_id", "unknown")
        state = res.get("state", "UNKNOWN")
        click.echo(f"  {i}. stage {stage_id} -> {state}")

    click.echo("-" * 50)
