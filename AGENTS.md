# AGENTS.md

This repo is a cookiecutter recipe. Do not treat any content in `annex/` as the source of truth. The source of truth is the recipe template under `{{ cookiecutter.package_name }}/` plus the root `tasks` workflow used to render, fix, verify, and diff a working copy.

## Rule 1: Change the recipe in a transfer-friendly way

When fixing formatting, typing, or developer-experience issues:

- prefer changes that map directly back to template files under `{{ cookiecutter.package_name }}/`
- avoid one-off fixes in the rendered example unless they are part of the refresh workflow
- avoid edits that depend on rendered concrete values like `example-cli`, `example_cli`, or `EXAMPLE_CLI` unless the point of the task is specifically to inspect rendered output
- keep placeholder-bearing recipe lines intact unless the template itself is intentionally changing

If you must inspect or iterate in rendered output, use the refresh workflow below and then apply the meaningful result back to the recipe.

## Rule 2: Use the root `tasks` workflow

Use the repo-root `./tasks` commands for recipe refresh work:

- `./tasks refresh-render-and-copy`
  - renders the current recipe into `annex/update/example-cli`
  - creates a working copy at `annex/update/example-cli-copy`

- `./tasks refresh-ruff-fix`
  - runs the rendered project's auto-fix workflow in the working copy

- make manual edits in:
  - `annex/update/example-cli-copy`

- `./tasks refresh-verify`
  - runs the rendered project's `./tasks check`

- `./tasks refresh-diff`
  - shows the filtered diff between the current recipe and the working copy
  - this is the default review view

- `./tasks refresh-single-render-and-copy`, `refresh-single-verify`, and
  `refresh-single-diff`
  - exercise the single-file branch using its dedicated replay fixture

- `./tasks refresh-check`
  - renders and verifies both supported layouts

- `./tasks refresh-diff-full`
  - shows the raw full diff
  - use this only when the filtered diff is giving unexpected results and you suspect it is hiding something important

## Rule 3: Prefer the filtered diff for transfer decisions

`refresh-diff` is designed to reduce noise from:

- template placeholder lines
- ignored/generated files from the working copy
- files intentionally excluded from review such as `LICENSE`

Use it to decide what should be copied back into the recipe.

Use `refresh-diff-full` only to debug the diffing process or inspect raw rendered churn.

## Rule 4: Fix format/type issues at the right layer

If a rendered working copy fails Ruff, formatter, or type checks:

1. reproduce through the root refresh workflow
2. make the minimal fix in the working copy if that helps discover the correct change
3. transfer the real fix back into `{{ cookiecutter.package_name }}/`
4. rerun:
   - `./tasks refresh-render-and-copy`
   - `./tasks refresh-verify`
   - `./tasks refresh-diff`

For changes shared by both layouts, run the corresponding `refresh-single-*`
commands as well. The packaged `app/cli_help.py` template is included directly
in the generated single-file executable, so help-engine changes require both
verification paths.

Do not stop at “the rendered copy passes.” The recipe itself must be updated so a fresh render passes.

## Rule 5: Be careful with generated Git state

Some refresh commands create temporary Git state in diff targets or working copies. That state is for comparison only. Do not rely on nested Git repos as the authoritative history or baseline for recipe edits.

## Rule 6: Keep the workflow maintainable

When editing the root `tasks` workflow:

- prefer inline bash recipes
- keep cache/data overrides for `uv`/`uvx` in place because sandboxed environments may not allow default cache paths
- prefer explicit, inspectable steps over clever templating or implicit state
- if you add diff filtering, keep it conservative and easy to reason about
