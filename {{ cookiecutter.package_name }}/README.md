# {{ cookiecutter.project_name }}

{{ cookiecutter.project_short_description }}

{% if cookiecutter.layout == "single-file" -%}
This project keeps the complete tool in the executable `{{ cookiecutter.package_name }}` so it can be copied to a colleague and run without installing a package. The script carries its Python dependencies in PEP 723 metadata and uses `uv` in its shebang.

Project-level support remains alongside it:

- `tests/` loads and exercises the extensionless script directly;
- `DEVELOPMENT.md` documents the CLI and help contracts;
- `AGENTS.md` gives automated contributors concise maintenance rules;
- `./tasks` provides consistent lint, format, type, and test commands.

## Quick start

```bash
./{{ cookiecutter.package_name }} --help
./{{ cookiecutter.package_name }} help foobar --no-pager
./{{ cookiecutter.package_name }} --baz 2
./tasks check
```

The generated script includes Stake-style concise and detailed help, terminal-aware paging and color, a Readline-safe Rich console, an argument-safe `duct` subprocess helper, and a small example command. Its stdout remains available for pipeable command results; diagnostics and interactive prompts should use the stderr-backed console.

## Sharing the tool

Copy only `{{ cookiecutter.package_name }}` to a machine with `uv` installed. The executable shebang resolves the declared dependencies automatically:

```bash
scp {{ cookiecutter.package_name }} colleague:~/bin/
```

Keep the surrounding project when developing the tool so changes retain tests, reviewable documentation, and standard checks.

## Adding behavior

Keep the operation as ordinary functions in `{{ cookiecutter.package_name }}` and put Cyclopts metadata at the CLI boundary. Register every operational command in `COMMANDS` and assign it exactly one purpose group. Preserve the first-paragraph/detailed-paragraph split in command and parameter help.

See [DEVELOPMENT.md](DEVELOPMENT.md) for the complete help and testing contract.
{% else -%}
This scaffold gives you:

- a Cyclopts-based CLI entrypoint
- an application-adapter/action split for command organization
- a `just`-based workflow for linting, formatting, type-checking, and tests
- concise and detailed Stake-style CLI help with terminal paging

## Quick start

```bash
uv sync
./tasks check
uv run {{ cookiecutter.package_name }} --help
uv run {{ cookiecutter.package_name }} help foobar --no-pager
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
    foobar.py
    app/
        __init__.py
        cli_help.py
        config.py
        console.py
        context.py
        daemon.py
        errors.py
        shell.py
        cli/
            __init__.py
            foobar.py
tests/
    test_cli.py
    test_config.py
```

Use `app/` for the CLI, parser adapters, and shared application infrastructure. Put each underlying action directly in `src/{{ cookiecutter.package }}/` so the tool's reusable behavior is immediately visible and remains callable without constructing parser state.

## Adding a command

1. Add an action module directly under `src/{{ cookiecutter.package }}/`.
2. Add its CLI wrapper under `src/{{ cookiecutter.package }}/app/cli/`.
3. Register the command name in `src/{{ cookiecutter.package }}/app/cli/__init__.py`.

Example action:

```python
from __future__ import annotations

import duct

from {{ cookiecutter.package }}.app import run_command, success


def greet(name: str, count: int) -> None:
    for _ in range(count):
        run_command(duct.cmd("echo", f"Hello {name}!"))
    success(f"Greeted {name} {count} times.")
```

Example CLI wrapper:

```python
from __future__ import annotations

from {{ cookiecutter.package }} import greet as action


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

See [DEVELOPMENT.md](DEVELOPMENT.md) for the CLI help contract, command-writing
guidance, and the hidden-default lifecycle. Automated contributors should also
follow [AGENTS.md](AGENTS.md).

```bash
./tasks ruff
./tasks format check
./tasks ty
./tasks test
./tasks check
```
{% endif -%}
