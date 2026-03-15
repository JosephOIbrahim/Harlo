"""twin session — Manage Twin sessions."""

import json

import click

from ..ipc import send_command


@click.group()
def session():
    """Manage Twin sessions (start, close, status, list)."""
    pass


@session.command("start")
@click.option("--domain", default="general", help="Session domain")
@click.option("--encoder", default="semantic", type=click.Choice(["lexical", "semantic"]), help="Encoder type")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def session_start(domain: str, encoder: str, as_json: bool):
    """Start a new session."""
    result = send_command("session_start", {"domain": domain, "encoder_type": encoder})

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
        click.echo(f"Session started: {data.get('session_id', 'unknown')}")


@session.command("close")
@click.argument("session_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def session_close(session_id: str, as_json: bool):
    """Close a session by ID."""
    result = send_command("session_close", {"session_id": session_id})

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
        click.echo(f"Session closed: {session_id} ({data.get('exchange_count', 0)} exchanges)")


@session.command("status")
@click.argument("session_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def session_status(session_id: str, as_json: bool):
    """Show status of a session."""
    result = send_command("session_status", {"session_id": session_id})

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
        _print_session(data)


@session.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for LLM consumption")
def session_list(as_json: bool):
    """List active sessions."""
    result = send_command("session_list", {})

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
        sessions = data.get("sessions", [])
        if not sessions:
            click.echo("No active sessions.")
            return
        click.echo(f"Active sessions ({len(sessions)}):")
        for s in sessions:
            click.echo(f"  {s['session_id']}  exchanges={s['exchange_count']}  domain={s['domain']}")


def _print_session(data: dict):
    """Print session info in human-readable format."""
    click.echo(f"Session: {data.get('session_id', 'unknown')}")
    click.echo(f"  Domain:     {data.get('domain', 'general')}")
    click.echo(f"  Exchanges:  {data.get('exchange_count', 0)}")
    click.echo(f"  Closed:     {data.get('closed', False)}")
    click.echo(f"  History:    {data.get('history_length', 0)} messages")
    click.echo(f"  Tokens:     {data.get('allostatic_tokens', 0)}")
