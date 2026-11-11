"""Repeated CLI invocations retain process-like isolation."""

import logging
import os
import signal
import sys

import cli_runner
import pytest
from cli_runner import COMMANDS, run_cli
{% if cookiecutter.layout != "single-file" %}
from {{ cookiecutter.package }}.app import context
{% endif %}

def test_all_command_help_is_order_independent():
    baseline = {command: run_cli("help", command, "--no-pager") for command in COMMANDS}
    for command in reversed(COMMANDS):
        assert run_cli(command, "--help").returncode == 0
        repeated = run_cli("help", command, "--no-pager")
        original = baseline[command]
        assert (repeated.returncode, repeated.stdout, repeated.stderr) == (
            original.returncode,
            original.stdout,
            original.stderr,
        )


def test_each_invocation_has_fresh_registration_and_context(monkeypatch):
    original = cli_runner.dispatch
    seen_apps, initial_flags = [], []

    def dispatch(args, *, application):
        seen_apps.append(application)
{% if cookiecutter.layout == "single-file" %}
        initial_flags.append(cli_runner.tool._DRY_RUN)
{% else %}
        initial_flags.append(context.get_context().dry_run)
{% endif %}
        original(args, application=application)
        application.command(lambda: None, name="leaked-command")

    monkeypatch.setattr(cli_runner, "dispatch", dispatch)
    assert run_cli("--dry-run", "--baz", "1").returncode == 0
    result = run_cli("--help")
    assert result.returncode == 0 and "leaked-command" not in result.stdout
    assert seen_apps[0] is not seen_apps[1]
    assert initial_flags == [False, False]


def test_global_state_is_restored_even_when_dispatch_raises(monkeypatch):
    root = logging.getLogger()
    logger = logging.getLogger("{{ cookiecutter.package }}.runner-test")
    handlers, level = root.handlers[:], root.level
    named_handlers, named_level = logger.handlers[:], logger.level
    argv, hook = sys.argv, sys.excepthook
{% if cookiecutter.layout != "single-file" %}
    previous_context = context.get_context()
{% endif %}
    sigint = signal.getsignal(signal.SIGINT)
    monkeypatch.setenv("CLI_RUNNER_SENTINEL", "original")
    assert "CLI_RUNNER_NEW_VALUE" not in os.environ

    def broken_dispatch(*_args, **_kwargs):
        os.environ["CLI_RUNNER_SENTINEL"] = "changed"
        os.environ["CLI_RUNNER_NEW_VALUE"] = "new"
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        sys.excepthook = lambda *_: None
        message = "unexpected CLI failure"
        raise RuntimeError(message)

    with monkeypatch.context() as patch:
        patch.setattr(cli_runner, "dispatch", broken_dispatch)
        with pytest.raises(RuntimeError, match="unexpected CLI failure"):
            run_cli("--help")
    assert os.environ["CLI_RUNNER_SENTINEL"] == "original"
    assert "CLI_RUNNER_NEW_VALUE" not in os.environ
    assert root.handlers == handlers and root.level == level
    assert logger.handlers == named_handlers and logger.level == named_level
    assert sys.argv is argv
{% if cookiecutter.layout != "single-file" %}
    assert context.get_context() is previous_context
{% endif %}
    assert sys.excepthook is hook and signal.getsignal(signal.SIGINT) == sigint
    assert run_cli("--help").returncode == 0
