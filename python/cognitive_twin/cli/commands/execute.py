"""twin execute — Execute an action plan."""

import json

import click

from ..ipc import send_command


@click.command()
@click.argument("plan_id")
@click.option("--step", type=int, default=None, help="Execute only a specific step")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def execute(plan_id: str, step: int, as_json: bool):
    """Execute action plan PLAN_ID, optionally a single --step."""
    args = {"plan_id": plan_id}
    if step is not None:
        args["step"] = step

    result = send_command("execute", args)

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
        _print_human(data, plan_id, step)


def _print_human(data: dict, plan_id: str, step):
    """Print execution results in human-readable format."""
    state = data.get("state", "unknown")
    executed = data.get("executed_steps", [])

    if step is not None:
        click.echo(f"Plan {plan_id} step {step}: {state}")
    else:
        click.echo(f"Plan {plan_id}: {state}")

    click.echo("-" * 50)
    for s in executed:
        idx = s.get("step", "?")
        st = s.get("state", "unknown")
        click.echo(f"  Step {idx}: {st}")
    click.echo("-" * 50)
