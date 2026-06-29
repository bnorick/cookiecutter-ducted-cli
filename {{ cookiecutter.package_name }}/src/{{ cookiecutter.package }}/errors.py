"""Error handling and exception formatting.

Provides custom exception classes, a Rich-formatted exception hook, and
signal handlers for graceful shutdown.

Usage::

    from {{ cookiecutter.package }} import (
        CliError,
        NotFoundError,
        install_exception_hook,
        install_signal_handler,
        exit,
    )

    install_exception_hook()
    install_signal_handler()

    if not found:
        raise NotFoundError("Config file not found")

    exit("Done!", code=0)
"""

from __future__ import annotations

import signal
import sys
from typing import Any

from {{ cookiecutter.package }}.console import _console, is_interactive

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class CliError(Exception):
    """Base exception for user-facing CLI errors.

    These errors are displayed nicely without a full traceback.

    Args:
        message: Error message.
        exit_code: Exit code to use when the error causes termination.
    """

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class NotFoundError(CliError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, exit_code=1)


class ConfigurationError(CliError):
    """Raised when there is a configuration problem."""

    def __init__(self, message: str = "Configuration error") -> None:
        super().__init__(message, exit_code=2)


class ValidationError(CliError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(message, exit_code=3)


# ---------------------------------------------------------------------------
# Exception hook
# ---------------------------------------------------------------------------


def install_exception_hook() -> None:
    """Install a custom exception hook for Rich-formatted error display.

    * :class:`CliError` exceptions show only the message (no traceback).
    * Other exceptions show a full Rich traceback in interactive mode.
    * ``KeyboardInterrupt`` is passed through to the default handler.
    """

    def _hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        if isinstance(exc_value, CliError):
            _console.print(f"[bold red]Error: {exc_value.message}[/bold red]")
            return

        if is_interactive():
            try:
                from rich.traceback import Traceback

                tb = Traceback.from_exception(exc_type, exc_value, exc_traceback)
                _console.print(tb)
            except Exception:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
        else:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------


def install_signal_handler() -> None:
    """Install signal handlers for graceful Ctrl+C / SIGTERM shutdown.

    Prints a nice message and exits with code 130 (standard for SIGINT).
    """

    def _handler(signum: int, frame: Any) -> None:
        _console.print("\n[bold yellow]Interrupted[/bold yellow]")
        sys.exit(130 if signum == signal.SIGINT else 143)

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


# ---------------------------------------------------------------------------
# Exit helper
# ---------------------------------------------------------------------------


def exit(message: str = "", code: int = 0) -> None:
    """Exit the program with an optional styled message.

    Args:
        message: Message to print before exiting.
        code: Exit code (0 = success, non-zero = error).
    """
    if message:
        if code != 0:
            _console.print(f"[bold red]{message}[/bold red]")
        else:
            _console.print(f"[bold green]{message}[/bold green]")
    sys.exit(code)
