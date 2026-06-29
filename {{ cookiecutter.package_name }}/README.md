# {{ cookiecutter.project_name }}

{{ cookiecutter.project_short_description }}

This scaffold gives you:

- a Cyclopts-based CLI entrypoint
- a small action/CLI split for command organization
- a `just`-based workflow for linting, formatting, type-checking, and tests

## Quick start

```bash
uv sync
./tasks check
uv run {{ cookiecutter.package_name }} --help
```

You can also run the CLI module directly:

```bash
uv run python -m {{ cookiecutter.package }} --help
```

## Project layout

```text
src/{{ cookiecutter.package }}/
    __init__.py
    __main__.py
    cli/
        __init__.py
        foobar.py
    actions/
        __init__.py
        foobar.py
tests/
    test_cli.py
    test_config.py
```

Use `cli/` for argument handling and user-facing command behavior. Use `actions/` for the underlying work so it stays testable and reusable outside the command parser.

## Adding a command

1. Add an action in `src/{{ cookiecutter.package }}/actions/`.
2. Add a CLI wrapper in `src/{{ cookiecutter.package }}/cli/`.
3. Register the command name in `src/{{ cookiecutter.package }}/cli/__init__.py`.

Example action:

```python
from __future__ import annotations

import duct

from {{ cookiecutter.package }} import run_command, success


def greet(name: str, count: int) -> None:
    for _ in range(count):
        run_command(duct.cmd("echo", f"Hello {name}!"))
    success(f"Greeted {name} {count} times.")
```

Example CLI wrapper:

```python
from __future__ import annotations

from {{ cookiecutter.package }}.actions import greet as action


def greet(name: str, count: int = 1) -> None:
    action.greet(name=name, count=count)
```

## Configuration

`ValueResolver` uses this precedence:

1. environment variables
2. CLI arguments
3. TOML config
4. defaults

Example:

```python
port = resolver.get(
    env="{{ cookiecutter.env_var_prefix }}_PORT",
    arg="port",
    config="{{ cookiecutter.package_name }}.server.port",
    default=8080,
    type=int,
)
```

If you use `Config.load()`, config files are resolved from `{{ cookiecutter.env_var_prefix }}_CONFIG_DIR` unless you pass `config_dir` explicitly.

## Development

```bash
./tasks ruff
./tasks format check
./tasks ty
./tasks test
./tasks check
```
