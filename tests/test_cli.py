import re

import pytest
from typer.testing import CliRunner

from htr_cli.cli import app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

EXPECTED_SUBCOMMANDS = {
    "init",
    "scaffold",
    "pull-transkribus",
    "port-escriptorium",
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


def test_split_dataset_lists_custom_split_flags():
    result = runner.invoke(app, ["split-dataset", "--help"])
    assert result.exit_code == 0
    # Rich colorizes flag names by wrapping each `-{token}` chunk in its own ANSI
    # span, which breaks plain substring checks under CI's FORCE_COLOR=1.
    plain = _ANSI_RE.sub("", result.stdout)
    for flag in ("--custom-train", "--custom-val", "--custom-test"):
        assert flag in plain, f"missing {flag} in split-dataset --help"
