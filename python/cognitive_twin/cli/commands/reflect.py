"""twin reflect — Run DMN reflection synthesis."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def reflect(as_json: bool):
    """Run DMN reflection synthesis on recent traces."""
    result = send_command("reflect", {})

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
    """Print reflection results in human-readable format."""
    insights = data.get("insights", [])
    synthesis = data.get("synthesis", "")

    click.echo("DMN Reflection Synthesis")
    click.echo("-" * 50)

    if synthesis:
        click.echo(f"  {synthesis}")
        click.echo()

    if insights:
        click.echo(f"  Insights ({len(insights)}):")
        for i, ins in enumerate(insights, 1):
            click.echo(f"    {i}. {ins}")
    else:
        click.echo("  No new insights.")

    click.echo("-" * 50)
