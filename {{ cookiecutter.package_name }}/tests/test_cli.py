from __future__ import annotations

import subprocess
import sys

from {{ cookiecutter.package }}.app.cli import COMMANDS


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - test arguments are fixed by the test suite.
        [sys.executable, "-m", "{{ cookiecutter.package }}", *args],
        check=False,
        capture_output=True,
        text=True,
    )


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
    result = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "help", "missing", "--no-pager"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "there is no command `missing`" in result.stderr


def test_help_command_has_concise_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "help", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage: {{ cookiecutter.package_name }} help [OPTIONS] [COMMAND]..." in result.stdout
    assert "--no-pager" in result.stdout


def test_verbose_level_counter_gates_diagnostics() -> None:
    plain = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )
    noisy = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "-vvv", "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert plain.returncode == 0
    assert noisy.returncode == 0
    assert "Will say 'foobar' 1 times" not in plain.stderr
    assert "Will say 'foobar' 1 times" in noisy.stderr
    assert noisy.stdout == "0 foobar\n"
