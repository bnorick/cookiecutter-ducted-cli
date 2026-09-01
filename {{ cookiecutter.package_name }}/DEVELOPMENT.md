# Developing {{ cookiecutter.project_name }}

## Workflow and structure

Use the project task runner from this directory:

```bash
./tasks test
./tasks check
```

{% if cookiecutter.layout == "single-file" -%}
The complete distributable tool lives in `{{ cookiecutter.package_name }}`. Keep
PEP 723 dependencies in its header accurate and preserve its executable bit.
Ordinary functions should hold reusable behavior; Cyclopts declarations, help
support, console utilities, and the entry point remain in the same file because
single-file portability is this layout's primary compatibility surface.

Tests load the extensionless script with `SourceFileLoader`. Importing it must
not execute `main()` or mutate external state.
{% else -%}
Application helpers live in `src/{{ cookiecutter.package }}/app/`; CLI setup and
per-command adapters live in its `cli/` package. Reusable action modules live
directly in `src/{{ cookiecutter.package }}/`; keep them callable without
constructing CLI parser state. Global runtime policy is carried through the
shared app context.
{% endif %}
## Help contract

The CLI follows the same split as `uv` and `stake`:

- `{{ cookiecutter.package_name }} [COMMAND] --help` prints concise reference
  help. It contains the first paragraph of each description and finishes with a
  `Use \`{{ cookiecutter.package_name }} help COMMAND\` for more details.` hint.
- `{{ cookiecutter.package_name }} help [COMMAND ...]` prints complete command
  documentation. On an interactive terminal it uses `$PAGER`, `less`, then
  `more`; `--no-pager` prints directly.

Successful help goes to stdout and exits zero. Invalid command paths and pager
failures go to stderr and exit nonzero. Redirected output is always plain text.
Interactive headings are bold green, command and option literals bold cyan, and
value placeholders cyan. The section order is description, usage, arguments,
command options, then global options. Multi-command indexes use a `Commands:`
heading and meaningful purpose headings ending in an en dash.

{% if cookiecutter.layout == "single-file" -%}
The help classes embedded in `{{ cookiecutter.package_name }}` own formatting,
paging, and hidden-default routing.
{% else -%}
`app/cli_help.py` owns formatting, paging, and hidden-default routing.
{% endif %}
The help system reads live Cyclopts metadata, so the only separately maintained
help data is the purpose group assigned during command registration.

## Writing help

Every visible command and parameter needs two layers when its behavior is not
trivial:

```python
help=(
    "Select the resumability store directory.\n\n"
    "The directory records completed work and must not be placed inside the "
    "destination tree. Reusing incompatible state fails explicitly."
)
```

The first paragraph must stand alone in a compact option table. The remaining
paragraphs should make invocation safe and predictable by documenting relevant
precedence, side effects, non-obvious defaults, constraints, compatibility, and
failure behavior. Keep tutorials, architecture discussions, and long example
collections in README.

Names, aliases, types, defaults, required state, and choices must come from
Cyclopts declarations. Never copy them into prose merely to make the formatter
work. Put global options in the shared `GlobalArgs` model and keep that section
last.

## Commands and the hidden default

Register every operational command in `COMMANDS` and assign it one purpose
group. While `COMMANDS` contains one entry, both forms work:

```bash
{{ cookiecutter.package_name }} ARGS
{{ cookiecutter.package_name }} COMMAND ARGS
```

Top-level help displays the operation directly and suppresses the redundant
command/category index. When adding a second operational command, the adapter
stops inserting the default and top-level help reveals all categories. That
changes the bare invocation contract: call it out in release notes, apply the
project's versioning policy, and provide migration guidance. The original
explicit form remains stable throughout.

## Paging and color

Detailed command help pages only when stdout is a TTY. `$PAGER` is parsed into
an argument vector and executed directly, never through a shell. An unset pager
falls back to `less -R`, then `more`. A configured pager is authoritative;
startup or nonzero-exit failures are reported. Early close/broken pipe is not an
error. `NO_COLOR`, redirection, and non-color-capable pagers receive plain text.

## Required tests

Help tests should cover:

- top-level hidden-default help and the explicit command form;
- concise versus detailed paragraph selection and the detailed-help hint;
- section order, exact headings, purpose-group coverage, aliases, and choices;
- plain captured output and forced-color output;
- `--no-pager`, configured/fallback pager selection, and early pager exit;
- invalid command paths on stderr with a nonzero status;
- the transition to grouped multi-command help, including disabled bare
  dispatch.

Run `./tasks check` before handoff.
