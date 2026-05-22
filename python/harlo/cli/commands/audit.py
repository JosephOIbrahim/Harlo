"""twin audit — Audit trail for resolutions and composition layers.

Two modes:
  - default:  read the append-only audit log for a stage or entry id.
  - --layers: list composition layers persisted under STAGES_DIR,
              optionally filtered by --provenance (source_type).
"""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("id", required=False)
@click.option(
    "--layers",
    is_flag=True,
    help="List composition layers instead of audit log entries.",
)
@click.option(
    "--provenance",
    default=None,
    help="Filter layers by provenance source_type (e.g. intake_calibrated).",
)
@click.option(
    "--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption"
)
def audit(id: str | None, layers: bool, provenance: str | None, as_json: bool):
    """Show the audit trail or composition layers for a stage."""
    if layers:
        return _show_layers(id, provenance, as_json)

    if not id:
        msg = "audit ID is required (or pass --layers to list composition layers)"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(2)

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


def _show_layers(stage_id: str | None, provenance: str | None, as_json: bool):
    args: dict = {}
    if stage_id:
        args["stage_id"] = stage_id
    if provenance:
        args["provenance"] = provenance
    result = send_command("audit_layers", args)

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
        return

    stages = data.get("stages", [])
    if not stages:
        if provenance:
            click.echo(f"  No layers match provenance={provenance}.")
        else:
            click.echo("  No composition layers found.")
        return

    for stage in stages:
        click.echo(f"Stage: {stage['stage_id']}")
        root = stage.get("merkle_root") or ""
        if root:
            click.echo(f"  Merkle root: {root[:16]}…")
        for layer in stage.get("layers", []):
            prov = (layer.get("provenance") or {}).get("source_type") or "—"
            click.echo(
                f"    [{layer.get('arc_type')}] {layer.get('layer_id')} "
                f"({prov}, source={layer.get('source')})"
            )
        click.echo()
    click.echo(f"  {data.get('layer_count', 0)} layer(s) across {len(stages)} stage(s)")


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
