"""twin export / twin import — Export and import twin data.

Honesty contract (CTO review D50): there is NO encrypted export format
yet. The previous interface accepted `--encrypted PATH` and silently
wrote a PLAINTEXT JSON dump of the entire memory store — a flag that
promised encryption and delivered none. That path now hard-fails.

Plaintext export remains available, but only under a flag that says
what it is. The exported file is chmod'd 0600 by the daemon handler.
"""

import json

import click

from ..ipc import send_command

_D50_MSG = (
    "encryption is not implemented yet — refusing to write a plaintext "
    "dump under an --encrypted flag (CTO review D50). Use "
    "--plaintext PATH to export unencrypted JSON (file mode 0600)."
)


@click.command("export")
@click.option("--encrypted", type=click.Path(), default=None,
              help="NOT IMPLEMENTED — hard-fails. No encrypted format exists yet.")
@click.option("--plaintext", type=click.Path(), default=None,
              help="Output path for a PLAINTEXT JSON export (mode 0600).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def export_cmd(encrypted: str | None, plaintext: str | None, as_json: bool):
    """Export twin data to a file. Plaintext only — see --help."""
    if encrypted is not None:
        if as_json:
            click.echo(json.dumps({"error": _D50_MSG}))
        else:
            click.echo(f"Error: {_D50_MSG}", err=True)
        raise SystemExit(1)
    if plaintext is None:
        msg = "an output path is required: use --plaintext PATH"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    result = send_command("export", {"path": plaintext, "encrypted": False})

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
        click.echo(f"Exported (PLAINTEXT) to: {plaintext}")


@click.command("import")
@click.option("--encrypted", type=click.Path(), default=None,
              help="NOT IMPLEMENTED — no encrypted format exists. "
                   "Files from `harlo export` are plaintext JSON; use --plaintext.")
@click.option("--plaintext", type=click.Path(exists=True), default=None,
              help="Path to a plaintext JSON export file.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def import_cmd(encrypted: str | None, plaintext: str | None, as_json: bool):
    """Import twin data from a plaintext JSON export file."""
    if encrypted is not None:
        msg = (
            "no encrypted format exists yet (CTO review D50). If this file "
            "came from `harlo export`, it is plaintext JSON — use --plaintext."
        )
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    if plaintext is None:
        msg = "an input path is required: use --plaintext PATH"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    result = send_command("import", {"path": plaintext, "encrypted": False})

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
        click.echo(f"Imported from: {plaintext}")
