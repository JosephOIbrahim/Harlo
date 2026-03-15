"""CLI entry point for the Cognitive Twin.

Uses Click framework. All commands: human-readable default, --json for LLM.
"""

import click

from .commands.ask import ask
from .commands.audit import audit
from .commands.boundaries import boundaries
from .commands.compose import compose
from .commands.conflicts import conflicts
from .commands.consent import consent
from .commands.consolidate import consolidate
from .commands.deferred import deferred
from .commands.execute import execute
from .commands.export_import import export_cmd, import_cmd
from .commands.inquire import inquire
from .commands.inquiries import inquiries
from .commands.mode import mode
from .commands.modulate import modulate
from .commands.motor_reflexes import motor_reflexes
from .commands.park import park
from .commands.plan import plan
from .commands.profile import profile
from .commands.recall import recall
from .commands.reflect import reflect
from .commands.session import session
from .commands.reflexes import reflexes
from .commands.resolve import resolve
from .commands.status import status
from .commands.stuck import stuck
from .commands.trace import trace
from .commands.undo import undo
from .commands.verify import verify


@click.group()
@click.version_option(version="6.0.0", prog_name="twin")
def cli():
    """The Cognitive Twin v6.0-MOTOR — biologically-architected AI memory."""
    pass


# Register commands
cli.add_command(ask)
cli.add_command(audit)
cli.add_command(boundaries)
cli.add_command(compose)
cli.add_command(conflicts)
cli.add_command(consent)
cli.add_command(consolidate)
cli.add_command(deferred)
cli.add_command(execute)
cli.add_command(export_cmd)
cli.add_command(import_cmd)
cli.add_command(inquire)
cli.add_command(inquiries)
cli.add_command(mode)
cli.add_command(modulate)
cli.add_command(motor_reflexes)
cli.add_command(park)
cli.add_command(plan)
cli.add_command(profile)
cli.add_command(recall)
cli.add_command(reflect)
cli.add_command(reflexes)
cli.add_command(resolve)
cli.add_command(session)
cli.add_command(status)
cli.add_command(stuck)
cli.add_command(trace)
cli.add_command(undo)
cli.add_command(verify)


def main():
    cli()


if __name__ == "__main__":
    main()
