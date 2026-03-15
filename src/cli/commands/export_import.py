"""twin export / twin import — Export and import encrypted twin data."""

import json

import click

from ..ipc import send_command


@click.command("export")
@click.option("--encrypted", required=True, type=click.Path(), help="Output path for encrypted export")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def export_cmd(encrypted: str, as_json: bool):
    """Export twin data to an encrypted file."""
    result = send_command("export", {"path": encrypted, "encrypted": True})

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
        click.echo(f"Exported to: {encrypted}")


@click.command("import")
@click.option("--encrypted", required=True, type=click.Path(exists=True), help="Path to encrypted import file")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def import_cmd(encrypted: str, as_json: bool):
    """Import twin data from an encrypted file."""
    result = send_command("import", {"path": encrypted, "encrypted": True})

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
        click.echo(f"Imported from: {encrypted}")
