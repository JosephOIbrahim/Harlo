"""twin boundaries — Manage operational boundaries."""

import json

import click

from ..ipc import send_command


@click.command()
@click.option("--add", "add_topic", default=None, help="Add a boundary topic")
@click.option("--remove", "remove_topic", default=None, help="Remove a boundary topic")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def boundaries(add_topic: str, remove_topic: str, as_json: bool):
    """Show, add, or remove operational boundaries."""
    args = {}
    if add_topic:
        args["action"] = "add"
        args["topic"] = add_topic
    elif remove_topic:
        args["action"] = "remove"
        args["topic"] = remove_topic
    else:
        args["action"] = "list"

    result = send_command("boundaries", args)

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
        _print_human(data, args)


def _print_human(data: dict, args: dict):
    """Print boundaries in human-readable format."""
    action = args.get("action", "list")

    if action == "add":
        click.echo(f"Added boundary: {args.get('topic', '')}")
    elif action == "remove":
        click.echo(f"Removed boundary: {args.get('topic', '')}")

    topics = data.get("boundaries", [])
    click.echo(f"Current boundaries ({len(topics)}):")
    click.echo("-" * 50)
    for i, topic in enumerate(topics, 1):
        click.echo(f"  {i}. {topic}")
    click.echo("-" * 50)
