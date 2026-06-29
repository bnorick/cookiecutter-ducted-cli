"""Runtime execution context and command runner.

Provides a global :class:`Context` for passing runtime state (verbose,
dry-run, config directory) and a :func:`run_command` helper that respects
those settings when executing duct expressions.
"""

from __future__ import annotations

import dataclasses
import pathlib
import shlex
import sys

import duct
import log

# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Context:
    """Global runtime context.

    Attributes:
        command: Original ``sys.argv`` used to invoke the CLI.
        config_dir: Path to the configuration directory.
        verbose: Print extra diagnostic output.
        quiet: Suppress non-essential output.
        dry_run: Show what would be done without executing.
    """

    command: list[str]
    config_dir: pathlib.Path | None = None
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False


CONTEXT = Context(command=list(sys.argv))


def get_context() -> Context:
    """Return the global runtime context."""
    return CONTEXT


# ---------------------------------------------------------------------------
# Shell command extraction
# ---------------------------------------------------------------------------


class _StopExtract(Exception):
    """Internal sentinel to break out of before_spawn callback."""


def _to_shell_command(command: duct.Expression) -> str:
    """Best-effort conversion of a duct Expression to a shell command string.

    Uses the ``before_spawn`` callback to inspect the command list that
    would be executed.
    """
    parts: list[str] = []

    def _extract(cmd: list[str], _kwargs: dict) -> None:
        parts.extend(cmd)
        raise _StopExtract()

    try:
        command.before_spawn(_extract).run()
    except _StopExtract:
        pass
    except Exception:
        pass

    if parts:
        return shlex.join(parts)
    return str(command)


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


def run_command(
    command: duct.Expression,
    dry_run: bool | None = None,
    verbose: bool | None = None,
) -> duct.Output:
    """Execute a duct command, respecting global context flags.

    Args:
        command: The duct expression to run.
        dry_run: Override the global dry-run setting.
        verbose: Override the global verbose setting.

    Returns:
        The ``duct.Output`` result (or a dummy success output in dry-run mode).
    """
    ctx = get_context()
    effective_dry_run = dry_run if dry_run is not None else ctx.dry_run
    effective_verbose = verbose if verbose is not None else ctx.verbose

    if effective_dry_run or effective_verbose:
        shell_cmd = _to_shell_command(command)
        log.info(f"Running command:\n  {shell_cmd}")

    if effective_dry_run:
        return duct.Output(status=0, stdout=None, stderr=None)

    return command.run()
