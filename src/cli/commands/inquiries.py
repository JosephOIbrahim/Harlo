"""twin inquiries — List or expire pending inquiries."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--expire", is_flag=True, help="Expire stale inquiries")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def inquiries(expire: bool, as_json: bool):
    """List pending inquiries, or expire stale ones with --expire."""
    result = send_command("inquiries", {"expire": expire})

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
        if expire:
            expired = data.get("expired", 0)
            click.echo(f"Expired {expired} stale inquiries.")
        else:
            items = data.get("inquiries", [])
            if not items:
                click.echo("No pending inquiries.")
                return
            click.echo(f"Pending inquiries ({len(items)}):")
            click.echo("-" * 50)
            for i, item in enumerate(items, 1):
                q = item.get("question", str(item))
                age = item.get("age", "")
                tag = f" (age: {age})" if age else ""
                click.echo(f"  {i}. {q}{tag}")
            click.echo("-" * 50)
