"""twin park — Store an idea/trace for later recall."""

import json
import uuid

import click

from ..ipc import send_command


@click.command()
@click.argument("idea")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--domain", default=None, help="Knowledge domain")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def park(idea: str, tags: str, domain: str, as_json: bool):
    """Park an IDEA for later recall."""
    trace_id = str(uuid.uuid4())
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    result = send_command("store", {
        "trace_id": trace_id,
        "message": idea,
        "tags": tag_list,
        "domain": domain,
        "source": "cli:park",
    })

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps({"trace_id": trace_id, "status": "parked"}, indent=2))
    else:
        click.echo(f"Parked. trace_id={trace_id}")
