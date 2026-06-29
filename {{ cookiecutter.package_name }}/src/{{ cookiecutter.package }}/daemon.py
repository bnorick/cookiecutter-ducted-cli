"""Daemon utilities for running long-running background processes.

Provides simple daemon management with PID files, signal handling, and
start/stop/status/restart operations.

Usage:
    from {{ cookiecutter.package }} import Daemon

    daemon = Daemon("myapp", pid_file="/run/myapp.pid")

    # Start
    daemon.start(my_main_loop)

    # Stop
    daemon.stop()

    # Check status
    if daemon.is_running:
        print(f"Running with PID {daemon.pid}")

CLI integration::

    from {{ cookiecutter.package }} import create_daemon_commands

    daemon = Daemon("myapp")
    for name, cmd in create_daemon_commands(daemon, my_main_loop).items():
        app.command(cmd, name=name)
"""

from __future__ import annotations

import contextlib
import grp
import os
import pathlib
import pwd
import signal
import sys
import time
from collections.abc import Callable
from typing import Any

import daemon
import daemon.pidfile
import log

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DaemonError(Exception):
    """Base exception for daemon operations."""


class DaemonAlreadyRunning(DaemonError):
    """Raised when trying to start an already-running daemon."""


class DaemonNotRunning(DaemonError):
    """Raised when trying to stop a non-running daemon."""


# ---------------------------------------------------------------------------
# Daemon class
# ---------------------------------------------------------------------------


class Daemon:
    """Simple daemon manager.

    Args:
        name: Daemon name (used for PID file and log messages).
        pid_file: Path to PID file (default: ``/run/{name}.pid``).
        working_dir: Working directory for the daemon process.
        stdout: Path for stdout redirect (default: ``/dev/null``).
        stderr: Path for stderr redirect (default: same as *stdout*).
        user: Username to drop privileges to (optional).
        group: Group name to drop privileges to (optional).
    """

    def __init__(
        self,
        name: str,
        pid_file: str | pathlib.Path | None = None,
        working_dir: str | pathlib.Path = "/",
        stdout: str | None = None,
        stderr: str | pathlib.Path | None = None,
        user: str | None = None,
        group: str | None = None,
    ) -> None:
        self.name = name
        self.pid_file = pathlib.Path(pid_file or f"/run/{name}.pid")
        self.working_dir = pathlib.Path(working_dir)
        self.stdout_path = stdout or "/dev/null"
        self.stderr_path = str(stderr) if stderr else self.stdout_path
        self.user = user
        self.group = group

    # ------------------------------------------------------------------
    # PID management
    # ------------------------------------------------------------------

    @property
    def pid(self) -> int | None:
        """Get the daemon PID if it is running, else ``None``."""
        if not self.pid_file.exists():
            return None
        try:
            pid = int(self.pid_file.read_text().strip())
            # Verify the process actually exists
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            # Stale PID file - clean it up
            self._clean_pid_file()
            return None

    @property
    def is_running(self) -> bool:
        """Check whether the daemon is currently running."""
        return self.pid is not None

    def _clean_pid_file(self) -> None:
        """Remove a stale PID file."""
        with contextlib.suppress(OSError):
            self.pid_file.unlink(missing_ok=True)

    def _resolve_uid(self) -> int | None:
        """Resolve the configured username to a uid, if provided."""
        if self.user is None:
            return None
        return pwd.getpwnam(self.user).pw_uid

    def _resolve_gid(self) -> int | None:
        """Resolve the configured group name to a gid, if provided."""
        if self.group is None:
            return None
        return grp.getgrnam(self.group).gr_gid

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, target: Callable, *args: Any, **kwargs: Any) -> None:
        """Start the daemon.

        Args:
            target: Callable to run as the daemon main loop.
            *args: Positional arguments for *target*.
            **kwargs: Keyword arguments for *target*.

        Raises:
            DaemonAlreadyRunning: If the daemon is already running.
        """
        if self.is_running:
            raise DaemonAlreadyRunning(f"Daemon '{self.name}' is already running (PID: {self.pid})")

        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

        stdout_f = open(self.stdout_path, "w")
        stderr_f = open(self.stderr_path, "w")

        pid_lock = daemon.pidfile.PIDLockFile(str(self.pid_file))

        from daemon import DaemonContext as DaemonContext

        with DaemonContext(
            pidfile=pid_lock,
            working_directory=str(self.working_dir),
            stdout=stdout_f,
            stderr=stderr_f,
            uid=self._resolve_uid(),
            gid=self._resolve_gid(),
            signal_map={
                signal.SIGTERM: self._signal_handler,
                signal.SIGINT: self._signal_handler,
                signal.SIGHUP: self._signal_handler,
            },
        ):
            log.info(f"Daemon '{self.name}' started (PID: {os.getpid()})")
            try:
                target(*args, **kwargs)
            finally:
                log.info(f"Daemon '{self.name}' exiting")

    def stop(self, timeout: int = 30) -> None:
        """Stop the daemon gracefully.

        Args:
            timeout: Seconds to wait before force-killing.

        Raises:
            DaemonNotRunning: If the daemon is not running.
        """
        pid = self.pid
        if pid is None:
            raise DaemonNotRunning(f"Daemon '{self.name}' is not running")

        log.info(f"Stopping daemon '{self.name}' (PID: {pid})")
        os.kill(pid, signal.SIGTERM)

        for _ in range(timeout * 10):
            if not self.is_running:
                log.info(f"Daemon '{self.name}' stopped")
                return
            time.sleep(0.1)

        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)
        self._clean_pid_file()

    def restart(self, target: Callable, *args: Any, **kwargs: Any) -> None:
        """Restart the daemon (stop then start)."""
        self.stop()
        self.start(target, *args, **kwargs)

    def status(self) -> dict:
        """Get daemon status as a dictionary.

        Returns:
            Dict with keys: ``name``, ``running``, ``pid``, ``pid_file``.
        """
        pid = self.pid
        return {
            "name": self.name,
            "running": pid is not None,
            "pid": pid,
            "pid_file": str(self.pid_file),
        }

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    @staticmethod
    def _signal_handler(signum: int, frame: Any) -> None:
        """Handle termination signals."""
        log.info(f"Received signal {signum}, shutting down")
        sys.exit(0)


# ---------------------------------------------------------------------------
# CLI command factory
# ---------------------------------------------------------------------------


def create_daemon_commands(
    daemon: Daemon,
    target: Callable,
    *target_args: Any,
    **target_kwargs: Any,
) -> dict[str, Callable]:
    """Create start/stop/status/restart functions for cyclopts integration.

    Args:
        daemon: A :class:`Daemon` instance.
        target: The main loop callable.
        *target_args: Args to pass to *target* on start.
        **target_kwargs: Kwargs to pass to *target* on start.

    Returns:
        Dict mapping command name to callable.

    Example:
        commands = create_daemon_commands(daemon, main_loop)
        app.command(commands["start"], name="start")
        app.command(commands["stop"], name="stop")
    """
    from {{ cookiecutter.package }}.console import _console as console
    from {{ cookiecutter.package }}.console import error

    def start_cmd() -> None:
        try:
            daemon.start(target, *target_args, **target_kwargs)
        except DaemonAlreadyRunning as exc:
            error(str(exc))
            sys.exit(1)

    def stop_cmd(force: bool = False) -> None:
        try:
            daemon.stop()
        except DaemonNotRunning as exc:
            error(str(exc))
            sys.exit(1)

    def status_cmd() -> None:
        s = daemon.status()
        if s["running"]:
            console.print(f"[bold green]✓[/bold green] {daemon.name} is running (PID: {s['pid']})")
        else:
            console.print(f"[bold red]✗[/bold red] {daemon.name} is not running")

    def restart_cmd() -> None:
        with contextlib.suppress(DaemonNotRunning):
            daemon.stop()
        try:
            daemon.start(target, *target_args, **target_kwargs)
        except Exception as exc:
            error(str(exc))
            sys.exit(1)

    return {
        "start": start_cmd,
        "stop": stop_cmd,
        "status": status_cmd,
        "restart": restart_cmd,
    }
