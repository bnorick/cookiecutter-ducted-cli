from __future__ import annotations

from cli_runner import COMMANDS, run_cli


def test_cli_help() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "Usage: {{ cookiecutter.package_name }}" in result.stdout
    assert "Global options:" in result.stdout
    assert "\x1b[" not in result.stdout


def test_every_operational_command_has_concise_and_detailed_help() -> None:
    for command in COMMANDS:
        concise = run_cli(command, "--help")
        detailed = run_cli("help", command, "--no-pager")

        assert concise.returncode == 0
        assert detailed.returncode == 0
        assert f"Use `{{ cookiecutter.package_name }} help {command}` for more details." in concise.stdout
        assert "for more details" not in detailed.stdout
        assert "Usage:" in concise.stdout
        assert "Usage:" in detailed.stdout


def test_unknown_help_path_is_an_error() -> None:
    result = run_cli("help", "missing", "--no-pager")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "there is no command `missing`" in result.stderr


def test_help_command_has_concise_help() -> None:
    result = run_cli("help", "--help")

    assert result.returncode == 0
    assert "Usage: {{ cookiecutter.package_name }} help [OPTIONS] [COMMAND]..." in result.stdout
    assert "--no-pager" in result.stdout
