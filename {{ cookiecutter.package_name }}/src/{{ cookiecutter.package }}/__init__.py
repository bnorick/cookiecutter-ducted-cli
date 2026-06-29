"""Public utility exports for {{ cookiecutter.project_name }}."""

from __future__ import annotations

import pathlib

# Configuration
from {{ cookiecutter.package }}.config import (
    Config,
    ValueResolver,
    load_config_safe,
)

# Console (rich)
from {{ cookiecutter.package }}.console import _console as console
from {{ cookiecutter.package }}.console import (
    confirm,
    error,
    info,
    is_interactive,
    panel,
    print,  # noqa: A004
    progress,
    prompt,
    rule,
    status,
    success,
    table,
    warn,
)
from {{ cookiecutter.package }}.console import init as console_init

# Runtime context
from {{ cookiecutter.package }}.context import Context as ExecutionContext
from {{ cookiecutter.package }}.context import get_context, run_command

# Daemon
from {{ cookiecutter.package }}.daemon import (
    Daemon,
    DaemonAlreadyRunning,
    DaemonError,
    DaemonNotRunning,
    create_daemon_commands,
)

# Errors
from {{ cookiecutter.package }}.errors import (
    CliError,
    ConfigurationError,
    NotFoundError,
    ValidationError,
    exit,  # noqa: A004
    install_exception_hook,
    install_signal_handler,
)

# Shell utilities
from {{ cookiecutter.package }}.shell import (
    cache_dir,
    capture,
    cd,
    command_exists,
    config_dir,
    copy_file,
    data_dir,
    ensure_dir,
    env,
    env_bool,
    env_int,
    env_list,
    exists,
    glob,
    home,
    iglob,
    is_dir,
    is_file,
    mkdtemp,
    mktemp,
    pipe,
    read_file,
    remove,
    retry,
    run,
    touch,
    which,
    write_file,
)

__all__ = [
    # Context
    "ExecutionContext",
    "get_context",
    "run_command",
    # Config
    "Config",
    "ValueResolver",
    "load_config_safe",
    # Console
    "console",
    "confirm",
    "error",
    "info",
    "console_init",
    "is_interactive",
    "panel",
    "print",
    "progress",
    "prompt",
    "rule",
    "status",
    "success",
    "table",
    "warn",
    # Shell
    "cache_dir",
    "capture",
    "cd",
    "command_exists",
    "config_dir",
    "copy_file",
    "data_dir",
    "ensure_dir",
    "env",
    "env_bool",
    "env_int",
    "env_list",
    "exists",
    "glob",
    "home",
    "iglob",
    "is_dir",
    "is_file",
    "mkdtemp",
    "mktemp",
    "pipe",
    "read_file",
    "remove",
    "retry",
    "run",
    "touch",
    "which",
    "write_file",
    # Errors
    "CliError",
    "ConfigurationError",
    "NotFoundError",
    "ValidationError",
    "exit",
    "install_exception_hook",
    "install_signal_handler",
    # Daemon
    "Daemon",
    "DaemonAlreadyRunning",
    "DaemonError",
    "DaemonNotRunning",
    "create_daemon_commands",
    # App paths
    "app_home",
    "app_config",
    "app_cache",
]

# ---------------------------------------------------------------------------
# Application-specific paths (XDG compliant)
# ---------------------------------------------------------------------------

_package_name = "{{ cookiecutter.package_name }}"


def app_home() -> pathlib.Path:
    """Return the application's home directory (~/.local/share/{package})."""
    return data_dir() / _package_name


def app_config() -> pathlib.Path:
    """Return the application's config directory (~/.config/{package})."""
    return config_dir() / _package_name


def app_cache() -> pathlib.Path:
    """Return the application's cache directory (~/.cache/{package})."""
    return cache_dir() / _package_name
