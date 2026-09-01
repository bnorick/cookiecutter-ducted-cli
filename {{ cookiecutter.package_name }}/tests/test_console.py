from __future__ import annotations

import importlib
import io

import pytest

from {{ cookiecutter.package }}.app.console import (
    _ANSI_ESCAPE_RE,
    ReadlineConsole,
    _mark_readline_nonprinting,
    info,
)
from {{ cookiecutter.package }}.app.context import CONTEXT


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


def test_info_is_gated_by_verbosity_level(monkeypatch: pytest.MonkeyPatch) -> None:
    from io import StringIO

    from rich.console import Console

    buffer = StringIO()
    module = importlib.import_module("{{ cookiecutter.package }}.app.console")
    monkeypatch.setattr(module, "_console", Console(file=buffer, force_terminal=False))

    try:
        CONTEXT.verbosity = 0
        info("hidden at level 0")
        assert "hidden at level 0" not in buffer.getvalue()

        CONTEXT.verbosity = 1
        info("shown at level 1")
        info("hidden at level 2", verbosity=2)
        assert "shown at level 1" in buffer.getvalue()
        assert "hidden at level 2" not in buffer.getvalue()

        CONTEXT.verbosity = 3
        info("deep reachable", verbosity=3)
        assert "deep reachable" in buffer.getvalue()
    finally:
        CONTEXT.verbosity = 0
