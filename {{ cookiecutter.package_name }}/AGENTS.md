# {{ cookiecutter.project_name }} development guide

Work from this project directory and use `./tasks` for formatting, typing, tests,
and the complete check. Preserve unrelated changes and keep stdout stable when a
command is designed for piping; diagnostics belong on stderr.

{% if cookiecutter.layout == "single-file" -%}
## Single-file architecture

- Keep all runtime code and PEP 723 dependencies in the executable
  `{{ cookiecutter.package_name }}`; it must remain useful when copied alone.
- Keep support material—tests, documentation, and task recipes—outside the
  script. Do not make the executable import it.
- Preserve the executable bit and the `uv run --no-config --script` shebang.
- Tests may load the extensionless script directly, but import must never run
  the command or perform external mutations.
{% else -%}
## Package architecture

- Keep reusable actions as top-level modules in `src/{{ cookiecutter.package }}/`.
- Keep framework helpers in `src/{{ cookiecutter.package }}/app/`, CLI setup in
  `app/cli/__init__.py`, and per-command adapters in `app/cli/COMMAND.py`.
{% endif %}
## CLI help rules

- Treat help text, command names, aliases, stdout, and exit codes as public
  interfaces.
- Put a complete one-sentence summary in the first paragraph of every visible
  command and parameter description. Put operational details after a blank line.
- Keep help in parser metadata. Do not maintain a separate hand-rendered option
  list or duplicate names, defaults, and choices in the formatter.
- `COMMAND --help` is concise. `help COMMAND` is detailed and pageable. Every
  concise command page ends with the detailed-help hint.
- Keep `Global options` last. Add each operational command to exactly one
  meaningful purpose group; the group is hidden while the tool has one command.
- A one-command tool accepts both bare and explicit command forms. When a second
  command is added, remove bare dispatch, reveal the groups, and document the
  compatibility change.
{% if cookiecutter.layout == "single-file" -%}
- Preserve the embedded Stake-style help layout and palette. Color must be
  terminal-aware and captured or redirected help must contain no ANSI escapes.
{% else -%}
- Preserve the Stake-style layout and palette implemented in `app/cli_help.py`.
  Color must be terminal-aware and captured or redirected help must contain no
  ANSI escapes.
{% endif -%}
- Add or update help regression tests whenever commands, parameters, groups,
  aliases, defaults, or long-form behavior change.

See `DEVELOPMENT.md` for the complete help contract and writing examples.
