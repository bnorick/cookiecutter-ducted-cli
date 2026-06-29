# cookiecutter-ducted-cli

A cookiecutter recipe for a Python CLI using `cyclopts` for arg parsing, `duct` for subprocess management, and `python-daemon` for daemonizing when needed.

Best used with `uv`,
```sh
uvx cookiecutter gh:bnorick/cookiecutter-ducted-cli
```

Other features of the recipe, such as task running via `./tasks`, use `uv` under the hood as well. In the case of `./tasks`, `uvx --from rust-just` is used to call `just`.