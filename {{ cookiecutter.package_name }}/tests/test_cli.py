from __future__ import annotations

import subprocess
import sys


def test_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "{{ cookiecutter.package }}", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "foobar" in result.stdout
