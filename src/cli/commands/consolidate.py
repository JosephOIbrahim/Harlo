"""twin consolidate — Run apoptosis and graph consolidation."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--verbose", is_flag=True, help="Show detailed consolidation info")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def consolidate(verbose: bool, as_json: bool):
    """Run apoptosis (DELETE + VACUUM) and graph consolidation."""
    result = send_command("consolidate", {"verbose": verbose})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        _print_human(result, verbose)


def _print_human(data: dict, verbose: bool):
    """Print consolidation results in human-readable format."""
    micro = data.get("microglia", {})
    consol = data.get("consolidation", {})

    click.echo("Consolidation complete.")
    click.echo("-" * 40)

    deleted = micro.get("traces_deleted", 0)
    size_before = micro.get("size_before", 0)
    size_after = micro.get("size_after", 0)
    click.echo(f"  Apoptosis: {deleted} traces deleted")
    if size_before or size_after:
        click.echo(f"  DB size:   {size_before} -> {size_after} bytes")

    edges = consol.get("edges_created", 0)
    clusters = consol.get("clusters", 0)
    click.echo(f"  Graph:     {edges} edges, {clusters} clusters")

    if verbose:
        for key, val in consol.items():
            if key not in ("edges_created", "clusters"):
                click.echo(f"  {key}: {val}")

    click.echo("-" * 40)
