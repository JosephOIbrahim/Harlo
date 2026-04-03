"""twin compose — Add a layer to a composition stage."""

import json

import click

from ..ipc import send_command

VALID_ARC_TYPES = ["local", "inherit", "variant", "reference", "payload", "sublayer"]


@click.command()
@click.option("--add-layer", required=True, help="Layer data as JSON string")
@click.option("--stage", required=True, help="Stage ID")
@click.option("--arc-type", required=True, type=click.Choice(VALID_ARC_TYPES), help="Arc type for the layer")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def compose(add_layer: str, stage: str, arc_type: str, as_json: bool):
    """Add a layer to a composition stage."""
    # Validate JSON input
    try:
        layer_data = json.loads(add_layer)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON for --add-layer: {e}"
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    result = send_command("compose", {
        "stage_id": stage,
        "layer_data": layer_data,
        "arc_type": arc_type,
    })

    if result.get("status") == "error":
        msg = result.get("message", "Unknown error")
        if as_json:
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    compose_data = result.get("result", {})

    if as_json:
        click.echo(json.dumps(compose_data, indent=2))
    else:
        _print_human(compose_data, stage, arc_type)


def _print_human(data: dict, stage_id: str, arc_type: str):
    """Print compose results in human-readable format."""
    layer_id = data.get("layer_id", "n/a")
    layer_count = data.get("layer_count", 0)

    click.echo(f"Compose: added layer to stage {stage_id}")
    click.echo(f"  Layer ID:    {layer_id}")
    click.echo(f"  Arc type:    {arc_type}")
    click.echo(f"  Total layers: {layer_count}")
    click.echo("-" * 50)
