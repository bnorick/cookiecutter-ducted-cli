"""Real-process entry-point, execution, terminal, and pager contracts."""

from __future__ import annotations

import os
import subprocess
import sys
{% if cookiecutter.layout == "single-file" %}
import pytest
from cli_runner import COMMANDS, SCRIPT, run_cli

# Compare application output without uv bootstrap installation diagnostics.
# The copied-script test below separately exercises the executable shebang.
CLI = [sys.executable, str(SCRIPT)]
{% else -%}
from pathlib import Path

import pytest
from cli_runner import COMMANDS, run_cli

CLI = [sys.executable, "-m", "{{ cookiecutter.package }}"]
{% endif %}

@pytest.fixture(autouse=True)
def cli_environment(monkeypatch):
    """Keep cold-process output independent of the developer's terminal."""
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("LINES", "24")
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("DEBUG", raising=False)


def run_cli_process(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run({{ "  # noqa: S603 - fixed test arguments." if cookiecutter.layout == "package" else "" }}
        [*CLI, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    "args",
    [
        ("--help",),
        (COMMANDS[0], "--help"),
        ("help", COMMANDS[0], "--no-pager"),
        ("help", "missing", "--no-pager"),
        ("help", "--help"),
        (COMMANDS[0], "--baz", "not-an-int"),
    ],
)
def test_module_entry_point_matches_isolated_dispatch(args):
    actual = run_cli_process(*args)
    expected = run_cli(*args)
    assert (actual.returncode, actual.stdout, actual.stderr) == (
        expected.returncode,
        expected.stdout,
        expected.stderr,
    )
    assert "\x1b[" not in actual.stdout + actual.stderr


{% if cookiecutter.layout == "single-file" -%}
def test_copied_script_runs_without_project_files(tmp_path):
    import shutil

    script = tmp_path / "{{ cookiecutter.package_name }}"
    shutil.copy2(SCRIPT, script)
    result = subprocess.run(
        [str(script), "--baz", "1"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "0 foobar\n"

{% else -%}
def test_installed_entry_point_matches_module():
    script = Path(sys.executable).with_name("{{ cookiecutter.package_name }}")
    result = subprocess.run([str(script), "--help"], check=False, capture_output=True, text=True, timeout=30)  # noqa: S603
    expected = run_cli("--help")
    assert (result.returncode, result.stdout, result.stderr) == (
        expected.returncode,
        expected.stdout,
        expected.stderr,
    )


def test_verbose_level_counter_gates_diagnostics() -> None:
    plain = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )
    noisy = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "-vvv", "--baz", "1"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert plain.returncode == 0
    assert noisy.returncode == 0
    assert "Will say 'foobar' 1 times" not in plain.stderr
    assert "Will say 'foobar' 1 times" in noisy.stderr
    assert noisy.stdout == "0 foobar\n"

{% endif %}
def terminal_cli(*args):
    """Exercise real isatty behavior while draining the pseudo-terminal."""
    import errno
    import pty
    from concurrent.futures import ThreadPoolExecutor

    master, slave = pty.openpty()

    def read_output():
        chunks = []
        while True:
            try:
                chunk = os.read(master, 8192)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode().replace("\r\n", "\n")

    try:
        with ThreadPoolExecutor(max_workers=1) as reader:
            output = reader.submit(read_output)
            try:
                result = subprocess.run({{ "  # noqa: S603 - fixed interpreter and test arguments." if cookiecutter.layout == "package" else "" }}
                    [*CLI, *args],
                    stdout=slave,
                    stderr=subprocess.PIPE,
                    check=False,
                    text=True,
                    timeout=30,
                )
            finally:
                os.close(slave)
            return subprocess.CompletedProcess(result.args, result.returncode, output.result(timeout=5), result.stderr)
    finally:
        os.close(master)


@pytest.mark.parametrize("pager_exit, expected", [(0, 0), (141, 0), (23, 2)])
def test_terminal_pager_and_exit_status(tmp_path, monkeypatch, pager_exit, expected):
    import shlex

    captured = tmp_path / "pager-input.txt"
    pager = tmp_path / "pager.py"
    pager.write_text(
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[1]).write_text(sys.stdin.read())\n"
        "print('pager invoked')\n"
        "raise SystemExit(int(sys.argv[2]))\n"
    )
    monkeypatch.setenv("PAGER", shlex.join([sys.executable, str(pager), str(captured), str(pager_exit)]))
    result = terminal_cli("help", COMMANDS[0])
    assert result.returncode == expected
    assert result.stdout == "pager invoked\n"
    expected_text = run_cli("help", COMMANDS[0], "--no-pager").stdout
    assert captured.read_text() == expected_text
    if expected:
        assert "pager exited with status 23" in result.stderr
    else:
        assert result.stderr == ""


def test_terminal_no_pager_and_no_color(tmp_path, monkeypatch):
    missing = str(tmp_path / "missing-pager")
    monkeypatch.setenv("PAGER", missing)
    monkeypatch.setenv("NO_COLOR", "1")
    result = terminal_cli("help", COMMANDS[0], "--no-pager")
    assert result.returncode == 0
    assert result.stderr == ""
    assert "Usage: {{ cookiecutter.package_name }}" in result.stdout
    assert "\x1b[" not in result.stdout
    failed = terminal_cli("help", COMMANDS[0])
    assert failed.returncode == 2
    assert "failed to start pager" in failed.stderr


def test_terminal_concise_help_uses_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    result = terminal_cli(COMMANDS[0], "--help")
    assert result.returncode == 0 and result.stderr == ""
    assert "\x1b[1;32m" in result.stdout
    assert "\x1b[1;36m" in result.stdout
