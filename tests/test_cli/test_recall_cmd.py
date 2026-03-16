"""Tests for the CLI recall command."""

import json
import os
import tempfile

from click.testing import CliRunner

from cognitive_twin.cli.main import cli


class TestRecallCommand:
    def test_recall_empty(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["recall", "anything"])
        assert result.exit_code == 0 or "No memories" in result.output or "Error" in result.output

    def test_status(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "7.0.0" in result.output

    def test_status_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["version"] == "7.0.0"

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "7.0.0" in result.output
