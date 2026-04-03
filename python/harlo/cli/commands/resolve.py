"""twin resolve — Resolve a composition stage using LIVRPS."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--stage", required=True, help="Stage ID to resolve")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def resolve(stage: str, as_json: bool):
    """Resolve a composition stage using LIVRPS opinion ordering."""
    result = send_command("resolve", {"stage_id": stage})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    resolution = result.get("result", {})

    if as_json:
        click.echo(json.dumps(resolution, indent=2))
    else:
        _print_human(resolution, stage)


def _print_human(data: dict, stage_id: str):
    """Print resolution results in human-readable format."""
    merkle_root = data.get("merkle_root", "n/a")
    attrs = data.get("resolved_attributes", {})
    conflicts = data.get("conflicts", [])

    click.echo(f"Resolution: stage {stage_id}")
    click.echo(f"  Merkle root: {merkle_root}")
    click.echo("-" * 50)

    if attrs:
        click.echo("  Resolved attributes:")
        for key, val in attrs.items():
            click.echo(f"    {key} = {val}")
    else:
        click.echo("  No resolved attributes.")

    if conflicts:
        click.echo(f"\n  Conflicts ({len(conflicts)}):")
        for i, conflict in enumerate(conflicts, 1):
            attr = conflict.get("attribute", "?")
            layers = conflict.get("layers", [])
            click.echo(f"    {i}. {attr} — contested by {len(layers)} layers")
    else:
        click.echo("\n  No conflicts detected.")

    click.echo("-" * 50)
