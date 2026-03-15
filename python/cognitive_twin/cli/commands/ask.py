"""twin ask — Query the Twin with full LLM generation loop."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("question")
@click.option("--provider", default="claude", type=click.Choice(["claude", "openai"]), help="LLM provider")
@click.option("--depth", type=click.Choice(["normal", "deep"]), default="normal", help="Context recall depth")
@click.option("--domain", default="general", help="Domain for verification depth")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
@click.option("--stream", "do_stream", is_flag=True, help="Stream the response")
def ask(question: str, provider: str, depth: str, domain: str, as_json: bool, do_stream: bool):
    """Ask the Twin a question with full context recall and LLM generation."""
    result = send_command("ask", {
        "question": question,
        "provider": provider,
        "depth": depth,
        "domain": domain,
    })

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    ask_data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(ask_data, indent=2))
    else:
        _print_human(ask_data, question)


def _print_human(data: dict, question: str):
    """Print ask results in human-readable format."""
    response = data.get("response", "")
    model = data.get("model", "unknown")
    confidence = data.get("confidence", 0.0)
    verification = data.get("verification", {})
    context_traces = data.get("context_traces", [])
    state = verification.get("state", "unknown")

    click.echo(f"Twin ({model}) — verification: {state}")
    click.echo("=" * 50)
    click.echo(response)
    click.echo("=" * 50)

    if context_traces:
        click.echo(f"\nContext: {len(context_traces)} traces recalled (confidence: {confidence:.2f})")
