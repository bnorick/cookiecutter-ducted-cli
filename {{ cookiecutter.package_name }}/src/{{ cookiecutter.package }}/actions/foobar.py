"""Example action - demonstrates value resolution and command execution."""

from __future__ import annotations

import dataclasses
from typing import Any, Self

import duct
import log

from {{ cookiecutter.package }} import get_context, run_command
from {{ cookiecutter.package }}.config import ValueResolver, load_config_safe


@dataclasses.dataclass
class FoobarArgs:
    """Resolved arguments for the foobar action."""

    baz: int

    @classmethod
    def resolve(cls, *, baz: int | None = None) -> Self:
        """Resolve *baz* from env > arg > config > default.

        Precedence:
        1. ``{{ cookiecutter.env_var_prefix }}_FOOBAR_BAZ`` environment variable
        2. Command-line argument
        3. TOML config key ``{{ cookiecutter.package_name }}.foobar.baz``
        4. Hardcoded default (``1``)
        """
        context = get_context()
        config = load_config_safe(context.config_dir)
        resolver = ValueResolver(args={"baz": baz}, config=config)

        baz = resolver.get(
            env="{{ cookiecutter.env_var_prefix }}_FOOBAR_BAZ",
            arg="baz",
            config="{{ cookiecutter.package_name }}.foobar.baz",
            default=1,
            required=False,
            type=int,
            desc="number of foobars",
        )

        return cls(baz=baz)

    def as_kwargs(self) -> dict[str, Any]:
        """Return args as a keyword dict for unpacking."""
        return {"baz": self.baz}


def foobar(baz: int) -> None:
    """Core foobar logic.

    Args:
        baz: Number of iterations.
    """
    log.debug("foobar action")

    for i in range(baz):
        log.info(f"I want to say '{i} foobar'")
        run_command(duct.cmd("echo", f"{i} foobar"))
