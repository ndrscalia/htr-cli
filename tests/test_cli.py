import pytest
from typer.testing import CliRunner

from htr_cli.cli import app

runner = CliRunner()

EXPECTED_SUBCOMMANDS = {
    "init",
    "scaffold",
    "pull-transkribus",
    "data-extraction",
    "split-dataset",
    "process-images",
    "process-images-tfe",
}


def test_root_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_root_help_lists_every_subcommand():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    missing = {cmd for cmd in EXPECTED_SUBCOMMANDS if cmd not in result.stdout}
    assert not missing, f"missing subcommands in --help output: {sorted(missing)}"


@pytest.mark.parametrize("subcommand", sorted(EXPECTED_SUBCOMMANDS))
def test_subcommand_help_exits_zero(subcommand):
    result = runner.invoke(app, [subcommand, "--help"])
    assert result.exit_code == 0, result.stdout


def test_unknown_subcommand_fails():
    result = runner.invoke(app, ["definitely-not-a-real-command"])
    assert result.exit_code != 0
