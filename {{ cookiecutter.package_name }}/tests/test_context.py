from __future__ import annotations

import duct

from {{ cookiecutter.package }}.app.context import CONTEXT, run_command


def test_run_command_skips_execution_in_dry_run() -> None:
    CONTEXT.dry_run = True
    try:
        result = run_command(duct.cmd("echo", "hi").stdout_capture())
    finally:
        CONTEXT.dry_run = False

    assert result.status == 0
    assert result.stdout is None


def test_run_command_always_run_executes_during_dry_run() -> None:
    CONTEXT.dry_run = True
    try:
        result = run_command(duct.cmd("echo", "hi").stdout_capture(), always_run=True)
    finally:
        CONTEXT.dry_run = False

    assert result.status == 0
    assert result.stdout == b"hi\n"
