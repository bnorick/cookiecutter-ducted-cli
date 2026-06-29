"""CLI application entry point.

Sets up the cyclopts application with global options and lazy command
registration.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
from typing import Annotated

import cyclopts
import log

from {{ cookiecutter.package }} import (
    console_init,
    get_context,
    install_exception_hook,
    install_signal_handler,
)


@dataclasses.dataclass
class GlobalArgs:
    """Global CLI options available on every subcommand."""

    config_dir: pathlib.Path | None = None
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False


def app_launcher(
    *tokens: Annotated[str, cyclopts.Parameter(show=False, allow_leading_hyphen=True)],
    global_args: Annotated[GlobalArgs, cyclopts.Parameter(name="*")] | None = None,
) -> None:
    """Meta-command launcher - runs before every subcommand."""
    # Apply global flags to the runtime context
    context = get_context()
    if global_args is not None:
        context.config_dir = global_args.config_dir
        context.verbose = global_args.verbose
        context.quiet = global_args.quiet
        context.dry_run = global_args.dry_run

    # Also respect environment variable for config dir
    env_config_dir = os.getenv("{{ cookiecutter.env_var_prefix }}_CONFIG_DIR")
    if env_config_dir:
        context.config_dir = pathlib.Path(env_config_dir).expanduser().resolve()

    # Parse and dispatch
    command, bound, ignored = app.parse_args(tokens)
    log.debug(f"{command=} {bound=} {ignored=}")
    log.debug(f"{context=}")
    command(*bound.args, **bound.kwargs)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = cyclopts.App(
    default_parameter=cyclopts.Parameter(negative=(), consume_multiple=True),
)
app["--help"].group = "Global options"
app["--version"].group = "Global options"
app.meta.group_parameters = cyclopts.Group("Global options", sort_key=0)

# Lazy command registration
COMMANDS = ("foobar",)
for _cmd in COMMANDS:
    app.command(
        f"{{ cookiecutter.package }}.cli.{_cmd}:{_cmd}",
        default_parameter=cyclopts.Parameter(group=cyclopts.Group(f"{_cmd} options")),
    )

# Meta-default launcher
app.meta.default(app_launcher)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Main entry point (wired to [project.scripts] in pyproject.toml)."""
    debug = os.environ.get("DEBUG") == "1"
    log.init(debug=debug)
    install_exception_hook()
    install_signal_handler()
    console_init(debug=debug)
    app.meta()
