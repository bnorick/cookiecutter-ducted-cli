from __future__ import annotations

from {{ cookiecutter.package }}.app.config import ValueResolver


def test_value_resolver_precedence() -> None:
    resolver = ValueResolver(args={"baz": 2})

    value = resolver.get(
        arg="baz",
        config="{{ cookiecutter.package_name }}.foobar.baz",
        default=1,
        required=False,
        type=int,
    )

    assert value == 2
