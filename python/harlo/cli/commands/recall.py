"""twin recall — Query the Association Engine."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("query")
@click.option("--depth", type=click.Choice(["normal", "deep"]), default="normal", help="Recall depth")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def recall(query: str, depth: str, as_json: bool):
    """Recall memories matching QUERY from the Association Engine."""
    result = send_command("recall", {"query": query, "depth": depth})

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    recall_data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(recall_data, indent=2))
    else:
        _print_human(recall_data, query)


def _print_human(data: dict, query: str):
    """Print recall results in human-readable format."""
    traces = data.get("traces", [])
    confidence = data.get("confidence", 0.0)
    context = data.get("context", "")

    if not traces:
        click.echo(f"No memories found for: {query}")
        return

    click.echo(f"Recall: {query} (confidence: {confidence:.2f})")
    click.echo("-" * 50)

    for i, trace in enumerate(traces, 1):
        strength = trace.get("strength", 0.0)
        message = trace.get("message", "")
        distance = trace.get("distance", 0)
        domain = trace.get("domain", "")
        domain_tag = f" [{domain}]" if domain else ""

        click.echo(f"  {i}. {message}{domain_tag}")
        click.echo(f"     strength={strength:.4f}  distance={distance}")

    click.echo("-" * 50)
    click.echo(f"  {len(traces)} traces returned")
