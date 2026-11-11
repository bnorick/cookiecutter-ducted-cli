"""Isolated in-process CLI calls using the production router and parser."""

{% if cookiecutter.layout == "single-file" -%}
import contextlib
import importlib.machinery
import importlib.util
import io
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "{{ cookiecutter.package_name }}"
LOADER = importlib.machinery.SourceFileLoader("{{ cookiecutter.package }}_script", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
LOADER.exec_module(tool)
COMMANDS = tool.COMMANDS
create_app = tool.create_app
dispatch = tool.dispatch
{% else -%}
import contextlib
import io
import logging
import os
import signal
import subprocess
import sys

import log
import log.settings
import log.state
import pytest

from {{ cookiecutter.package }}.app import context
from {{ cookiecutter.package }}.app.cli import COMMANDS as COMMANDS
from {{ cookiecutter.package }}.app.cli import create_app, dispatch
{% endif %}

def loggers():
    return [
        logging.getLogger(),
        *(logger for logger in logging.Logger.manager.loggerDict.values() if isinstance(logger, logging.Logger)),
    ]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Capture CLI streams and Python exit semantics without process startup."""
    stdout, stderr = io.StringIO(), io.StringIO()
    root = logging.getLogger()
    environment = dict(os.environ)
    logger_states = {
        logger: (logger.handlers[:], logger.filters[:], logger.level, logger.disabled, logger.propagate)
        for logger in loggers()
    }
    previous_disable = root.manager.disable
    previous_signals = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    previous_hook = sys.excepthook
    code = 0
    try:
        with (
            pytest.MonkeyPatch.context() as patch,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
{%- if cookiecutter.layout == "single-file" %}
            patch.setattr(tool, "_VERBOSITY", 0)
            patch.setattr(tool, "_DRY_RUN", False)
            patch.setattr(tool, "console", tool.ReadlineConsole(stderr=True))
{%- else %}
            patch.setattr(context, "CONTEXT", context.Context(command=["{{ cookiecutter.package_name }}", *args]))
{%- endif %}
            patch.setattr(sys, "argv", ["{{ cookiecutter.package_name }}", *args])
            for logger in logger_states:
                logger.handlers = []
                logger.filters = []
                logger.setLevel(logging.WARNING if logger is root else logging.NOTSET)
                logger.disabled = False
                logger.propagate = True
            logging.disable(logging.NOTSET)
{%- if cookiecutter.layout != "single-file" %}
            # Match run() before app_launcher emits its first minilog record.
            # Minilog snapshots the effective level into its named logger.
            patch.setattr(log.settings, "DEFAULT_LEVEL", logging.INFO)
            patch.setattr(log.state, "initialized", False)
            patch.setattr(log.state, "silenced", set())
            log.init(debug=os.environ.get("DEBUG") == "1")
{%- endif %}
            try:
                dispatch(list(args), application=create_app())
            except SystemExit as error:
                if error.code is None:
                    code = 0
                elif isinstance(error.code, int):
                    code = error.code
                else:
                    stderr.write(str(error.code) + "\n")
                    code = 1
    finally:
        original_handlers = {h for state in logger_states.values() for h in state[0]}
        for logger in loggers():
            for handler in logger.handlers:
                if handler not in original_handlers:
                    handler.close()
            handlers, filters, level, disabled, propagate = logger_states.get(
                logger,
                ([], [], logging.NOTSET, False, True),
            )
            logger.handlers = handlers
            logger.filters = filters
            logger.setLevel(level)
            logger.disabled = disabled
            logger.propagate = propagate
        logging.disable(previous_disable)
        for sig, handler in previous_signals.items():
            signal.signal(sig, handler)
        sys.excepthook = previous_hook
        os.environ.clear()
        os.environ.update(environment)
    return subprocess.CompletedProcess(["{{ cookiecutter.package_name }}", *args], code, stdout.getvalue(), stderr.getvalue())
