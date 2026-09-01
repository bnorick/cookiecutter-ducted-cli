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


def test_hidden_default_execution_shells_out_via_run_command() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--baz", "2"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == "0 foobar\n1 foobar\n"


def test_dry_run_prints_commands_without_executing() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--dry-run", "--baz", "2"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert "Would run:" in result.stderr
    assert "echo 0 foobar" in result.stderr
    assert "echo 1 foobar" in result.stderr


def test_verbose_logs_commands_and_still_executes() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--verbose", "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == "0 foobar\n"
    assert "Running:" in result.stderr
    assert "echo 0 foobar" in result.stderr


def test_run_command_always_run_executes_and_marks_during_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from io import StringIO

    from rich.console import Console

    executed: list[bool] = []

    class FakeCommand:
        def run(self) -> None:
            executed.append(True)

    def fake_cmd(*args: str) -> FakeCommand:
        return FakeCommand()

    buffer = StringIO()
    monkeypatch.setattr("duct.cmd", fake_cmd)
    monkeypatch.setattr(tool, "console", Console(file=buffer, force_terminal=False))
    monkeypatch.setattr(tool, "_DRY_RUN", True)
    tool.run_command("echo", "hi", always_run=True)
    tool.run_command("echo", "hi")

    assert executed == [True]
    output = buffer.getvalue()
    assert "Running (even in dry-run):" in output
    assert "Would run:" in output


def test_verbose_level_counter_enables_run_tracing() -> None:
    plain = subprocess.run(
        [str(SCRIPT), "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )
    noisy = subprocess.run(
        [str(SCRIPT), "-vvv", "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert plain.returncode == 0
    assert noisy.returncode == 0
    assert "Running:" not in plain.stderr
    assert "Running:" in noisy.stderr
    assert noisy.stdout == "0 foobar\n"
