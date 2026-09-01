from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).parents[1] / "{{ cookiecutter.package_name }}"
LOADER = importlib.machinery.SourceFileLoader("{{ cookiecutter.package }}_script", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
LOADER.exec_module(tool)


def test_script_is_executable() -> None:
    assert SCRIPT.stat().st_mode & 0o111


def test_mark_readline_nonprinting_wraps_ansi_sequences() -> None:
    prompt = "\x1b[1;32mcmd>\x1b[0m "

    assert tool._mark_readline_nonprinting(prompt) == "\x01\x1b[1;32m\x02cmd>\x01\x1b[0m\x02 "


def test_console_input_passes_colored_prompt_to_readline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readline_console = tool.ReadlineConsole(
        file=io.StringIO(),
        force_terminal=True,
        color_system="standard",
    )
    received_prompt = ""

    def fake_input(prompt: str) -> str:
        nonlocal received_prompt
        received_prompt = prompt
        return "yes"

    monkeypatch.setattr(tool, "_READLINE_AVAILABLE", True)
    monkeypatch.setattr("builtins.input", fake_input)

    assert readline_console.input("[bold red]Danger[/bold red]: ") == "yes"
    ansi_prompt = received_prompt.replace("\x01", "").replace("\x02", "")
    assert "\x1b[" in ansi_prompt
    assert received_prompt == tool._mark_readline_nonprinting(ansi_prompt)


def test_concise_and_detailed_help() -> None:
    concise = subprocess.run(
        [str(SCRIPT), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    detailed = subprocess.run(
        [str(SCRIPT), "help", "foobar", "--no-pager"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert concise.returncode == 0
    assert detailed.returncode == 0
    assert "Use `{{ cookiecutter.package_name }} help foobar` for more details." in concise.stdout
    assert "This example keeps pipeable data on stdout." not in concise.stdout
    assert "This example keeps pipeable data on stdout." in detailed.stdout


def test_hidden_default_execution() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--baz", "2"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == "foobar\nfoobar\n"
