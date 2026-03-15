"""twin reflexes — Manage cognitive reflex cache."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--list", "do_list", is_flag=True, help="List cached reflexes")
@click.option("--invalidate", default=None, help="Invalidate a reflex by hash")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def reflexes(do_list: bool, invalidate: str, as_json: bool):
    """List or invalidate cognitive reflexes."""
    args = {}
    if invalidate:
        args["action"] = "invalidate"
        args["hash"] = invalidate
    else:
        args["action"] = "list"

    result = send_command("reflexes", args)

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
        if invalidate:
            click.echo(f"Invalidated reflex: {invalidate}")
        else:
            items = data.get("reflexes", [])
            click.echo(f"Reflexes ({len(items)}):")
            click.echo("-" * 50)
            for i, r in enumerate(items, 1):
                h = r.get("hash", "?")
                desc = r.get("description", str(r))
                click.echo(f"  {i}. [{h[:8]}] {desc}")
            click.echo("-" * 50)
