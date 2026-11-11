# cookiecutter-ducted-cli

A cookiecutter recipe for Python CLIs using `cyclopts` for arg parsing and
`duct` for subprocess management. Choose the packaged layout for a conventional
`src/` project with application helpers, or the single-file layout for a
PEP 723 executable that can be copied and run on its own while retaining tests,
documentation, standardized help, and a Readline-safe console in its project.

Best used with `uv`,
```sh
uvx cookiecutter gh:bnorick/cookiecutter-ducted-cli
```

Other features of the recipe, such as task running via `./tasks`, use `uv` under the hood as well. In the case of `./tasks`, `uvx --from rust-just` is used to call `just`.


Generated projects test exhaustive help and parser behavior in-process using
fresh production parsers and isolated runtime state. A small subprocess suite
retains entry-point, real terminal/pager, and external-command guarantees in
both layouts. Run `./tasks refresh-check` here to verify fresh renders of both.
