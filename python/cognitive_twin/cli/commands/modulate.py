"""twin modulate — Adjust modulation parameters."""

import json

import click

from ..ipc import send_command


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
@click.pass_context
def modulate(ctx, as_json: bool):
    """Adjust modulation parameters (e.g. --curiosity 0.8 --caution 0.3)."""
    # Parse --dimension value pairs from extra args
    params = {}
    it = iter(ctx.args)
    for arg in it:
        if arg.startswith("--"):
            key = arg.lstrip("-")
            try:
                val = next(it)
                try:
                    val = float(val)
                except ValueError:
                    pass
                params[key] = val
            except StopIteration:
                click.echo(f"Error: --{key} requires a value", err=True)
                raise SystemExit(1)

    if not params:
        click.echo("Usage: twin modulate --<dimension> <value>", err=True)
        raise SystemExit(1)

    result = send_command("modulate", {"params": params})

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
        click.echo("Modulation updated:")
        for key, value in sorted(params.items()):
            click.echo(f"  {key} -> {value}")
