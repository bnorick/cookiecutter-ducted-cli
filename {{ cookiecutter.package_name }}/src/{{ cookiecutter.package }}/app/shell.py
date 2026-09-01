"""Shell-like utilities for running commands and file operations.

Provides bash-like helpers so that writing Python CLIs feels as natural as
writing bash scripts::

    from {{ cookiecutter.package }}.app import run, capture, pipe, cd, glob

    # Run a command (duct expression or shell string)
    run("ls -la")
    run(duct.cmd("echo", "hello"))

    # Capture output
    output = capture("echo hello")

    # Chain commands
    pipe("ls -la", "grep foo", "wc -l").run()

    # Change directory
    with cd("/tmp"):
        run("ls")

    # Glob files
    for f in glob("*.py"):
        print(f)

    # File I/O
    content = read_file("config.toml")
    write_file("output.txt", content)

    # Environment variables
    port = env_int("PORT", default=8080)
    debug = env_bool("DEBUG", default=False)
"""

from __future__ import annotations

import contextlib
import functools
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterator
from typing import Any

import duct
import log

from {{ cookiecutter.package }}.app.context import get_context, run_command

# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


def _to_duct_expr(cmd: duct.Expression | str) -> duct.Expression:
    """Convert a shell string or duct expression to a duct Expression."""
    if isinstance(cmd, str):
        return duct.cmd("sh", "-c", cmd)
    return cmd


def _cmd_description(cmd: duct.Expression | str) -> str:
    """Get a human-readable description of a command."""
    if isinstance(cmd, str):
        return cmd
    # Try to extract the command list via before_spawn
    parts: list[str] = []

    def _extract(c: list[str], _kwargs: dict) -> None:
        parts.extend(c)
        raise _StopExtract()

    class _StopExtract(Exception):
        pass

    try:
        cmd.before_spawn(_extract).run()
    except _StopExtract:
        pass
    except Exception:
        pass

    if parts:
        return shlex.join(parts)
    return str(cmd)


def run(
    cmd: duct.Expression | str,
    *,
    check: bool = True,
    dry_run: bool | None = None,
    verbose: bool | None = None,
) -> duct.Output:
    """Run a command with nice output.

    Args:
        cmd: A duct ``Expression`` or a shell command string.
        check: If ``True``, raise on non-zero exit status.
        dry_run: If ``True``, only print the command without executing.
        verbose: If ``True``, print the command before executing.

    Returns:
        The ``duct.Output`` result.

    Raises:
        RuntimeError: If *check* is ``True`` and the command fails.
    """
    ctx = get_context()
    effective_dry_run = dry_run if dry_run is not None else ctx.dry_run
    effective_verbose = verbose if verbose is not None else ctx.verbose

    desc = _cmd_description(cmd)

    if effective_dry_run or effective_verbose:
        log.info(f"$ {desc}")

    if effective_dry_run:
        return duct.Output(status=0, stdout=None, stderr=None)

    result = run_command(_to_duct_expr(cmd))

    if check and result.status != 0:
        raise RuntimeError(f"Command failed with status {result.status}: {desc}")

    return result


def capture(cmd: duct.Expression | str) -> str:
    """Capture command stdout.

    Args:
        cmd: A duct ``Expression`` or a shell command string.

    Returns:
        Command stdout as a decoded string (stripped of trailing newline).

    Example:
        >>> output = capture("echo hello")
        >>> output
        'hello'
    """
    expr = _to_duct_expr(cmd)
    result = expr.stdout_capture().run()
    return result.stdout.decode().rstrip() if result.stdout else ""


def pipe(*commands: duct.Expression | str) -> duct.Expression:
    """Chain commands with pipes (like bash ``|``).

    Args:
        *commands: Commands to chain (duct expressions or shell strings).

    Returns:
        A duct ``Expression`` representing the pipeline.

    Example:
        >>> pipe("ls -la", "grep foo", "wc -l").run()
    """
    exprs = [_to_duct_expr(c) for c in commands]
    result = exprs[0]
    for expr in exprs[1:]:
        result = result.pipe(expr)
    return result


# ---------------------------------------------------------------------------
# Directory operations
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def cd(path: str | os.PathLike[str]) -> Iterator[None]:
    """Change directory context manager.

    Args:
        path: Directory to change to.

    Example:
        with cd("/tmp"):
            run("ls -la")
        # back to original directory
    """
    original = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original)


# ---------------------------------------------------------------------------
# File / glob operations
# ---------------------------------------------------------------------------


def glob(
    pattern: str,
    root: str | os.PathLike[str] | None = None,
) -> list[pathlib.Path]:
    """Glob file pattern, returning sorted ``Path`` objects.

    Args:
        pattern: Glob pattern (e.g. ``"*.txt"``, ``"**/*.py"``).
        root: Root directory (default: current working directory).

    Returns:
        Sorted list of matching ``Path`` objects.
    """
    root = pathlib.Path(root) if root is not None else pathlib.Path.cwd()
    return sorted(root.glob(pattern))


def iglob(
    pattern: str,
    root: str | os.PathLike[str] | None = None,
) -> Iterator[pathlib.Path]:
    """Lazy glob file pattern.

    Args:
        pattern: Glob pattern.
        root: Root directory.

    Yields:
        Matching ``Path`` objects.
    """
    root = pathlib.Path(root) if root is not None else pathlib.Path.cwd()
    yield from sorted(root.glob(pattern))


def exists(path: str | os.PathLike[str]) -> bool:
    """Check if a path exists."""
    return pathlib.Path(path).exists()


def is_file(path: str | os.PathLike[str]) -> bool:
    """Check if a path is a file."""
    return pathlib.Path(path).is_file()


def is_dir(path: str | os.PathLike[str]) -> bool:
    """Check if a path is a directory."""
    return pathlib.Path(path).is_dir()


def read_file(path: str | os.PathLike[str], mode: str = "r") -> str | bytes:
    """Read file contents.

    Args:
        path: File path.
        mode: ``"r"`` for text, ``"rb"`` for binary.

    Returns:
        File contents.
    """
    p = pathlib.Path(path)
    if mode == "r":
        return p.read_text()
    return p.read_bytes()


def write_file(
    path: str | os.PathLike[str],
    content: str | bytes,
    mode: str = "w",
) -> pathlib.Path:
    """Write content to a file, creating parent directories as needed.

    Args:
        path: File path.
        content: Content to write.
        mode: ``"w"`` for text, ``"wb"`` for binary.

    Returns:
        The ``Path`` object.
    """
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == "w":
        if not isinstance(content, str):
            raise TypeError("text mode requires string content")
        p.write_text(content)
    else:
        if not isinstance(content, bytes):
            raise TypeError("binary mode requires bytes content")
        p.write_bytes(content)
    return p


def copy_file(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
) -> pathlib.Path:
    """Copy a file, creating parent directories as needed.

    Returns:
        The destination ``Path`` object.
    """
    dst_path = pathlib.Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst_path)
    return dst_path


def remove(path: str | os.PathLike[str], missing_ok: bool = True) -> None:
    """Remove a file or directory.

    Args:
        path: Path to remove.
        missing_ok: If ``True``, don't raise if the path doesn't exist.
    """
    p = pathlib.Path(path)
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=missing_ok)
    elif p.is_file():
        p.unlink(missing_ok=missing_ok)


# ---------------------------------------------------------------------------
# Temporary files / directories
# ---------------------------------------------------------------------------


def mktemp(
    suffix: str = "",
    prefix: str = "tmp",
    directory: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Create a temporary file.

    Returns:
        Path to the temporary file.
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
    os.close(fd)
    return pathlib.Path(path)


def mkdtemp(
    suffix: str = "",
    prefix: str = "tmp",
    directory: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Create a temporary directory.

    Returns:
        Path to the temporary directory.
    """
    return pathlib.Path(tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=directory))


# ---------------------------------------------------------------------------
# Environment variable helpers
# ---------------------------------------------------------------------------


def env(name: str, default: str = "") -> str:
    """Get an environment variable.

    Args:
        name: Variable name.
        default: Default value if not set.
    """
    return os.getenv(name, default)


def env_int(name: str, default: int = 0) -> int:
    """Get an environment variable as an integer."""
    return int(os.getenv(name, default))


def env_bool(name: str, default: bool = False) -> bool:
    """Get an environment variable as a boolean.

    Truthy values: ``1``, ``true``, ``yes``, ``on`` (case-insensitive).
    """
    val = os.getenv(name, "")
    if not val:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def env_list(name: str, separator: str = ",", default: list[str] | None = None) -> list[str]:
    """Get an environment variable as a comma-separated list.

    Args:
        name: Variable name.
        separator: List separator.
        default: Default list if not set.
    """
    val = os.getenv(name, "")
    if not val:
        return default or []
    return [item.strip() for item in val.split(separator) if item.strip()]


# ---------------------------------------------------------------------------
# Command lookup
# ---------------------------------------------------------------------------


def which(command: str) -> pathlib.Path | None:
    """Find an executable in ``PATH``.

    Returns:
        Path to the executable, or ``None`` if not found.
    """
    result = subprocess.run(  # noqa: S603
        ["which", command],  # noqa: S607
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return pathlib.Path(result.stdout.strip())
    return None


def command_exists(command: str) -> bool:
    """Check if a command exists in ``PATH``."""
    return which(command) is not None


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Retry decorator / context manager for transient failures.

    Args:
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries (seconds).
        backoff: Multiplier for delay after each retry.
        exceptions: Exception types to catch and retry.

    Example (decorator):
        @retry(max_attempts=3, delay=0.5)
        def fetch_url(url):
            ...

    Example (manual):
        for attempt in retry(max_attempts=3):
            try:
                result = flaky_operation()
                break
            except ConnectionError:
                if attempt.is_last:
                    raise
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: BaseException | None = None
            func_name = getattr(func, "__name__", func.__class__.__name__)
            for attempt_num in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt_num == max_attempts:
                        raise last_exception from exc
                    log.warn(
                        f"{func_name} failed (attempt {attempt_num}/{max_attempts}): "
                        f"{exc}. Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            if last_exception is None:
                raise RuntimeError("retry() exhausted without capturing an exception")
            raise last_exception

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def touch(path: str | os.PathLike[str]) -> pathlib.Path:
    """Create an empty file or update its timestamp.

    Creates parent directories as needed.
    """
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def ensure_dir(path: str | os.PathLike[str]) -> pathlib.Path:
    """Ensure a directory exists, creating it and parents as needed.

    Returns:
        The ``Path`` object.
    """
    p = pathlib.Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def home() -> pathlib.Path:
    """Return the user's home directory as a ``Path``."""
    return pathlib.Path.home()


def cache_dir() -> pathlib.Path:
    """Return the user's cache directory (XDG compliant)."""
    return pathlib.Path(os.getenv("XDG_CACHE_HOME", pathlib.Path.home() / ".cache"))


def config_dir() -> pathlib.Path:
    """Return the user's config directory (XDG compliant)."""
    return pathlib.Path(os.getenv("XDG_CONFIG_HOME", pathlib.Path.home() / ".config"))


def data_dir() -> pathlib.Path:
    """Return the user's local data directory (XDG compliant)."""
    return pathlib.Path(os.getenv("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share"))
