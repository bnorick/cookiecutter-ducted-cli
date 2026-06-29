"""Example CLI command."""

from __future__ import annotations

from {{ cookiecutter.package }} import get_context, info
from {{ cookiecutter.package }}.actions import foobar as action


def foobar(baz: int | None = None) -> None:
    """Say 'foobar' *baz* times.

    Args:
        baz: Number of times to say foobar (default: resolved from config/env).
    """
    args = action.FoobarArgs.resolve(baz=baz)

    ctx = get_context()
    if ctx.verbose:
        info(f"Will say 'foobar' {args.baz} times")

    action.foobar(**args.as_kwargs())
