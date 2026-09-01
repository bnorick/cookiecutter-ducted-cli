from __future__ import annotations

import importlib
import io

import pytest

from {{ cookiecutter.package }}.app.console import (
    _ANSI_ESCAPE_RE,
    ReadlineConsole,
    _mark_readline_nonprinting,
)


def test_mark_readline_nonprinting_wraps_ansi_sequences() -> None:
    prompt = "\x1b[1;32mcmd>\x1b[0m "

    assert _mark_readline_nonprinting(prompt) == "\x01\x1b[1;32m\x02cmd>\x01\x1b[0m\x02 "


def test_console_input_passes_colored_prompt_to_readline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readline_console = ReadlineConsole(
        file=io.StringIO(),
        force_terminal=True,
        color_system="standard",
    )
    received_prompt = ""

    def fake_input(prompt: str) -> str:
        nonlocal received_prompt
        received_prompt = prompt
        return "yes"

    console_module = importlib.import_module("{{ cookiecutter.package }}.app.console")
    monkeypatch.setattr(console_module, "_READLINE_AVAILABLE", True)
    monkeypatch.setattr("builtins.input", fake_input)

    assert readline_console.input("[bold red]Danger[/bold red]: ") == "yes"
    ansi_prompt = received_prompt.replace("\x01", "").replace("\x02", "")
    assert "\x1b[" in ansi_prompt
    assert received_prompt == _mark_readline_nonprinting(ansi_prompt)
    assert _ANSI_ESCAPE_RE.sub("", ansi_prompt) == "Danger: "
