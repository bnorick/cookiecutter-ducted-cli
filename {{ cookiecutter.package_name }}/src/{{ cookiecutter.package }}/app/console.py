"""Rich console utilities for interactive and non-interactive output.

Provides a pre-configured Rich Console that:
- Writes to stderr by default (keeping stdout clean for piping)
- Auto-detects interactive vs non-interactive mode
- Adapts output format accordingly

Usage:
    from {{ cookiecutter.package }}.app import console, success, error, status, table

    success("Operation completed")
    error("Something went wrong")

    with status("Processing..."):
        do_work()

    table("Results", ["Name", "Value"], [["a", "1"], ["b", "2"]])
"""

from __future__ import annotations

import re
import sys
from contextlib import redirect_stdout
from getpass import getpass
from typing import TYPE_CHECKING, Any, TextIO, cast

import log
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import TextType

from {{ cookiecutter.package }}.app.context import get_context

try:
    import readline  # noqa: F401 -- importing installs Python's line editor
except ImportError:
    _READLINE_AVAILABLE = False
else:
    _READLINE_AVAILABLE = True

if TYPE_CHECKING:
    from rich.status import Status as RichStatus


_ANSI_ESCAPE_RE = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~]|[@-Z\\-_])")
_READLINE_PROMPT_START_IGNORE = "\x01"
_READLINE_PROMPT_END_IGNORE = "\x02"


def _mark_readline_nonprinting(prompt: str) -> str:
    """Tell Readline that ANSI escape sequences occupy no screen columns."""
    return _ANSI_ESCAPE_RE.sub(
        lambda match: f"{_READLINE_PROMPT_START_IGNORE}{match.group(0)}{_READLINE_PROMPT_END_IGNORE}",
        prompt,
    )


class ReadlineConsole(Console):
    """A Rich console whose prompts remain intact while Readline edits input."""

    def input(
        self,
        prompt: TextType = "",
        *,
        markup: bool = True,
        emoji: bool = True,
        password: bool = False,
        stream: TextIO | None = None,
    ) -> str:
        prompt_str = ""
        if prompt:
            with self.capture() as capture:
                self.print(prompt, markup=markup, emoji=emoji, end="")
            prompt_str = capture.get()
        if self.legacy_windows:
            self.file.write(prompt_str)
            prompt_str = ""
        if password:
            return getpass(prompt_str, stream=stream)
        if stream:
            self.file.write(prompt_str)
            return stream.readline()
        if _READLINE_AVAILABLE:
            prompt_str = _mark_readline_nonprinting(prompt_str)
        # input() must receive the prompt so Readline knows its visible width.
        # Redirect its prompt output to this console's stderr-backed file.
        with redirect_stdout(self.file):
            return input(prompt_str)


# ---------------------------------------------------------------------------
# Global console instance - writes to stderr so stdout stays clean for piping
# ---------------------------------------------------------------------------
_console = ReadlineConsole(stderr=True, force_terminal=False)
# TODO: This cast works around a tooling conflict: ty rejects direct access to
# Rich Console runtime attributes like force_terminal/emoji, while Ruff rejects
# setattr() with constant attribute names. Check whether Rich exposes setter
# methods or another supported configuration path, and replace this workaround
# if so.
_console_runtime = cast(Any, _console)


# ---------------------------------------------------------------------------
# Interactivity detection
# ---------------------------------------------------------------------------


def is_interactive() -> bool:
    """Check if stderr is attached to an interactive terminal."""
    return sys.stderr.isatty()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init(
    debug: bool = False,
    force_color: bool = False,
    quiet: bool = False,
) -> None:
    """Initialize console and logging.

    Args:
        debug: Enable debug-level logging.
        force_color: Force colored output even when stderr is not a TTY.
        quiet: Suppress all non-essential output.
    """
    log.init(debug=debug)
    if force_color:
        _console_runtime.force_terminal = True
        _console.no_color = False
    elif not is_interactive():
        _console.no_color = True
        _console_runtime.emoji = False
    _console.quiet = quiet


# ---------------------------------------------------------------------------
# Convenience aliases on the global console
# ---------------------------------------------------------------------------


def print(*args: Any, **kwargs: Any) -> None:
    """Print to stderr using Rich formatting.

    Unlike :func:`builtins.print`, this writes to *stderr* so that stdout
    remains clean for piping.
    """
    _console.print(*args, **kwargs)


def rule(title: str = "") -> None:
    """Print a horizontal rule with an optional title."""
    from rich.rule import Rule

    _console.print(Rule(title))


# ---------------------------------------------------------------------------
# Status messages
# ---------------------------------------------------------------------------


def success(message: str) -> None:
    """Print a success message in green."""
    _console.print(f"[bold green]✓ {message}[/bold green]")


def error(message: str) -> None:
    """Print an error message in red."""
    _console.print(f"[bold red]✗ {message}[/bold red]")


def warn(message: str) -> None:
    """Print a warning message in yellow."""
    _console.print(f"[bold yellow]⚠ {message}[/bold yellow]")


def info(message: str, *, verbosity: int | None = None) -> None:
    """Print an informational message, gated by verbosity level.

    The message appears only when the active ``-v`` level reaches *verbosity*;
    ``None`` (the default) requests level 1.

    Args:
        message: Message to print.
        verbosity: Minimum verbosity level (repeat count of ``-v``) required.
            ``None`` means level 1.
    """
    level = 1 if verbosity is None else verbosity
    if get_context().verbosity >= level:
        _console.print(f"[bold blue]i {message}[/bold blue]")


# ---------------------------------------------------------------------------
# Progress & spinners
# ---------------------------------------------------------------------------


class _NoOpStatus:
    """No-op context manager for non-interactive mode."""

    def __enter__(self) -> _NoOpStatus:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def update(self, message: str) -> None:
        log.info(message)


class _NoOpProgress:
    """No-op progress bar for non-interactive mode."""

    def __enter__(self) -> _NoOpProgress:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def add_task(self, description: str, total: int | None = None, **kwargs: Any) -> int:
        log.info(f"{description} (total={total})")
        return 0

    def update(self, task_id: int, **kwargs: Any) -> None:
        if "description" in kwargs:
            log.info(kwargs["description"])

    def start(self) -> _NoOpProgress:
        return self

    def stop(self) -> None:
        pass


def status(message: str, spinner: str = "dots") -> RichStatus | _NoOpStatus:
    """Create a status spinner for long-running operations.

    In non-interactive mode the spinner is replaced with plain log messages.

    Args:
        message: Status message to display.
        spinner: Spinner style name (see rich.spinner).

    Returns:
        A context manager (Rich ``Status`` or no-op equivalent).

    Example:
        with status("Processing files...") as s:
            for f in files:
                process(f)
                s.update(f"Processing {f}")
    """
    if not is_interactive():
        log.info(message)
        return _NoOpStatus()
    return _console.status(message, spinner=spinner)


def progress(**kwargs: Any) -> Progress | _NoOpProgress:
    """Create a progress bar.

    In non-interactive mode the progress bar is replaced with plain log
    messages.

    Returns:
        A context manager (Rich ``Progress`` or no-op equivalent).

    Example:
        with progress() as prog:
            task = prog.add_task("Processing", total=100)
            for i in range(100):
                do_work(i)
                prog.update(task, advance=1)
    """
    if not is_interactive():
        return _NoOpProgress()
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=_console,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def confirm(question: str, default: bool = True) -> bool:
    """Ask a yes/no confirmation question.

    In non-interactive mode the default value is returned silently.

    Args:
        question: Question to ask.
        default: Default answer when not interactive.

    Returns:
        User's answer (``True`` / ``False``).
    """
    if not is_interactive():
        log.info(f"{question} (default: {'yes' if default else 'no'})")
        return default
    return Confirm.ask(question, default=default, console=_console)


def prompt(text: str, default: str = "", password: bool = False) -> str:
    """Prompt the user for text input.

    In non-interactive mode the default value is returned.

    Args:
        text: Prompt text.
        default: Default value when not interactive.
        password: If ``True``, hide input.

    Returns:
        User's input string.
    """
    if not is_interactive():
        return default
    return Prompt.ask(text, default=default, password=password, console=_console)


# ---------------------------------------------------------------------------
# Tables & panels
# ---------------------------------------------------------------------------


def table(
    title: str = "",
    headers: list[str] | None = None,
    data: list[list[str]] | None = None,
    **kwargs: Any,
) -> Table:
    """Create and print a formatted table.

    Args:
        title: Table title.
        headers: Column headers.
        data: Table rows.

    Returns:
        The Rich ``Table`` (also printed to console).

    Example:
        table(
            "Files",
            ["Name", "Size", "Type"],
            [["file1.txt", "1 KB", "text"], ["file2.bin", "2 MB", "binary"]],
        )
    """
    t = Table(title=title, **kwargs)
    if headers:
        for h in headers:
            t.add_column(h)
    if data:
        for row in data:
            t.add_row(*row)
    _console.print(t)
    return t


def panel(title: str = "", text: str = "", **kwargs: Any) -> None:
    """Print a panel with optional title and text.

    Args:
        title: Panel title.
        text: Panel content (supports Rich markup).
    """
    from rich.panel import Panel

    _console.print(Panel(text, title=title, **kwargs))
