"""Example CLI command."""

from __future__ import annotations

from typing import Annotated

import cyclopts

from {{ cookiecutter.package }} import foobar as action
from {{ cookiecutter.package }}.app import info


def foobar(
    baz: Annotated[
        int | None,
        cyclopts.Parameter(
            help="Number of times to say foobar.\n\n"
            "The value is resolved from CLI, environment, configuration, then the built-in default."
        ),
    ] = None,
) -> None:
    """Say 'foobar' *baz* times.

    Resolves the requested count through the normal configuration layers, then invokes the reusable
    action once for each requested message. Dry-run and output policy are supplied by global context.

    Args:
        baz: Number of times to say foobar (default: resolved from config/env).
    """
    args = action.FoobarArgs.resolve(baz=baz)

    info(f"Will say 'foobar' {args.baz} times", verbosity=1)

    action.foobar(**args.as_kwargs())
