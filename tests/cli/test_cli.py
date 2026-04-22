"""Make sure the CLI doesn't explode."""

from click.testing import CliRunner

from pidgin.cli.run import run


def test_cli_runs():
    """Make sure the CLI actually starts."""
    runner = CliRunner()

    # Use --quiet so it doesn't wait for daemon
    result = runner.invoke(
        run,
        ["-a", "local:test", "-b", "local:test", "-t", "1", "-p", "Test", "--quiet"],
    )

    # Exit code 0 = success
    assert result.exit_code == 0


def test_cli_help_works():
    """Make sure --help doesn't crash."""
    runner = CliRunner()

    result = runner.invoke(run, ["--help"])

    # Should succeed
    assert result.exit_code == 0
    # Should mention conversations
    assert "conversation" in result.output.lower()


def test_cli_spec_file_missing():
    """Make sure missing spec files are handled."""
    runner = CliRunner()

    result = runner.invoke(run, ["nonexistent.yaml"])

    # Should fail gracefully
    assert result.exit_code != 0
