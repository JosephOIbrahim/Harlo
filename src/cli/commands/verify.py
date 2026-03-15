"""twin verify — Verify a composition stage resolution via the Aletheia Engine."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("id")
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Verification depth",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def verify(id: str, depth: str, as_json: bool):
    """Verify a composition stage resolution via the Aletheia Verification Engine."""
    result = send_command("verify", {"stage_id": id, "depth": depth})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    verification = result.get("result", {})

    if as_json:
        click.echo(json.dumps(verification, indent=2))
    else:
        _print_human(verification, id)


def _print_human(data: dict, stage_id: str):
    """Print verification results in human-readable format."""
    state = data.get("state", "UNKNOWN")
    flaws = data.get("flaws", [])
    intent_alignment = data.get("intent_alignment", None)
    depth = data.get("depth", "standard")

    click.echo(f"Verification: stage {stage_id}")
    click.echo(f"  State: {state}")
    click.echo(f"  Depth: {depth}")
    click.echo("-" * 50)

    if intent_alignment is not None:
        click.echo(f"  Intent alignment: {intent_alignment:.2f}")

    if flaws:
        click.echo(f"\n  Flaws ({len(flaws)}):")
        for i, flaw in enumerate(flaws, 1):
            flaw_type = flaw.get("type", "unknown")
            description = flaw.get("description", "")
            severity = flaw.get("severity", "")
            severity_tag = f" [{severity}]" if severity else ""
            click.echo(f"    {i}. {flaw_type}{severity_tag}: {description}")
    else:
        click.echo("\n  No flaws detected.")

    click.echo("-" * 50)
