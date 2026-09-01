from __future__ import annotations

import subprocess
import sys


def test_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage: {{ cookiecutter.package_name }} [OPTIONS]" in result.stdout
    assert "Commands:" not in result.stdout
    assert "Arguments:" not in result.stdout
    assert "Options:" in result.stdout
    assert "Global options:" in result.stdout
    assert "Use `{{ cookiecutter.package_name }} help foobar` for more details." in result.stdout
    assert "\x1b[" not in result.stdout


def test_explicit_command_help_matches_hidden_default() -> None:
    root = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    explicit = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "foobar", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert explicit.returncode == 0
    assert explicit.stdout == root.stdout


def test_detailed_help_expands_later_paragraphs() -> None:
    concise = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "foobar", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    detailed = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "help", "foobar", "--no-pager"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert detailed.returncode == 0
    assert "requested count through the normal" not in concise.stdout
    assert "requested count through the normal" in detailed.stdout
    assert "resolved from CLI, environment, configuration" in detailed.stdout
    assert "for more details" not in detailed.stdout


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
