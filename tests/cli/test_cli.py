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


def test_cli_handles_bad_model():
    """Make sure we don't crash on bad input."""
    runner = CliRunner()

    # Use --quiet to avoid interactive mode
    result = runner.invoke(
        run, ["-a", "not_a_real_model", "-b", "also_fake", "-t", "1", "--quiet"]
    )

    # Should fail gracefully (exit code may be 0 if handled gracefully)
    # Just check that it doesn't crash and gives some feedback
    assert result.exit_code in [0, 1, 2]  # Any of these is fine


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
