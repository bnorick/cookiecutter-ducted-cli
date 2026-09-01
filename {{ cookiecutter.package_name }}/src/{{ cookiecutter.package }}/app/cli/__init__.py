"""CLI application entry point.

Sets up the cyclopts application with global options and lazy command
registration.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import sys
from typing import Annotated

import cyclopts
import log

from {{ cookiecutter.package }}.app import (
    console_init,
    get_context,
    install_exception_hook,
    install_signal_handler,
)
from {{ cookiecutter.package }}.app.cli_help import HelpConfig, HelpSystem


@dataclasses.dataclass
class GlobalArgs:
    """Global CLI options available on every subcommand."""

    config_dir: Annotated[
        pathlib.Path | None,
        cyclopts.Parameter(
            help="Directory containing the tool's TOML configuration.\n\n"
            "Overrides the standard per-user location. The {{ cookiecutter.env_var_prefix }}_CONFIG_DIR "
            "environment variable takes precedence when it is set."
        ),
    ] = None
    verbose: Annotated[
        int,
        cyclopts.Parameter(
            count=True,
            short_alias=True,
            negative=(),
            help="Increase verbosity.\n\n"
            "Repeat for more detail (``-v``, ``-vv``, ``-vvv``). Higher levels add resolution and "
            "execution details to stderr without changing data output; ``--verbose`` is shorthand for ``-v``.",
        ),
    ] = 0
    quiet: Annotated[
        bool,
        cyclopts.Parameter(
            help="Suppress non-essential status output.\n\n"
            "Errors remain visible and still produce a nonzero exit status."
        ),
    ] = False
    dry_run: Annotated[
        bool,
        cyclopts.Parameter(
            help="Plan the operation without applying changes.\n\n"
            "Configuration and validation still run, but persistent external state is not mutated."
        ),
    ] = False


def app_launcher(
    *tokens: Annotated[str, cyclopts.Parameter(show=False, allow_leading_hyphen=True)],
    global_args: Annotated[GlobalArgs, cyclopts.Parameter(name="*")] | None = None,
) -> None:
    """Meta-command launcher - runs before every subcommand."""
    # Apply global flags to the runtime context
    context = get_context()
    if global_args is not None:
        context.config_dir = global_args.config_dir
        context.verbosity = global_args.verbose
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
    help="{{ cookiecutter.project_short_description }}",
    help_format="plaintext",
    default_parameter=cyclopts.Parameter(negative=(), consume_multiple=True),
)
GLOBAL_OPTIONS = cyclopts.Group("Global options", sort_key=100)
app["--help"].group = GLOBAL_OPTIONS
app["--version"].group = GLOBAL_OPTIONS

# Lazy command registration
COMMANDS = ("foobar",)
CORE_COMMANDS = cyclopts.Group("Core", sort_key=10)
for _cmd in COMMANDS:
    app.command(
        f"{{ cookiecutter.package }}.app.cli.{_cmd}:{_cmd}",
        group=CORE_COMMANDS,
        default_parameter=cyclopts.Parameter(group=cyclopts.Group("Options", sort_key=0)),
    )
    app[_cmd]["--help"].group = GLOBAL_OPTIONS
    app[_cmd]["--version"].group = GLOBAL_OPTIONS


def help_command(
    *command: Annotated[
        str,
        cyclopts.Parameter(
            help="Command path to document.\n\n"
            "Omit the path to document the current top-level interface. Nested command names are "
            "resolved one component at a time."
        ),
    ],
    no_pager: Annotated[
        bool,
        cyclopts.Parameter(
            help="Print detailed help without a pager.\n\n"
            "This is useful for redirection, automated checks, and terminals where the configured "
            "pager is not desired."
        ),
    ] = False,
) -> None:
    """Display detailed documentation for a command.

    Detailed help expands every command and option description and uses a terminal pager when one
    is available. Normal execution is intercepted by the shared help system before dispatch.
    """
    del command, no_pager


app.command(help_command, name="help", group=cyclopts.Group("General", sort_key=90))
app["help"]["--help"].group = GLOBAL_OPTIONS
app["help"]["--version"].group = GLOBAL_OPTIONS

# Meta-default launcher
app.meta.default(app_launcher)
app.meta.group_parameters = GLOBAL_OPTIONS


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
    help_system = HelpSystem(
        app,
        HelpConfig(
            program="{{ cookiecutter.package_name }}",
            default_command=COMMANDS[0],
            operational_commands=COMMANDS,
        ),
    )
    args = help_system.run(sys.argv[1:])
    if args is not None:
        app.meta(args)
