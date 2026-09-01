from __future__ import annotations

import cyclopts

from {{ cookiecutter.package }}.app.cli import COMMANDS, app
from {{ cookiecutter.package }}.app.cli_help import HelpConfig, HelpSystem, Pager


def config(*commands: str) -> HelpConfig:
    return HelpConfig(
        program="{{ cookiecutter.package_name }}",
        default_command="foobar",
        operational_commands=commands,
    )


def test_single_command_is_an_implicit_default() -> None:
    help_system = HelpSystem(app, config(*COMMANDS))

    assert help_system.normalize(["--dry-run"]) == ["foobar", "--dry-run"]
    assert help_system.normalize(["foobar", "--dry-run"]) == ["foobar", "--dry-run"]


def test_multiple_commands_disable_implicit_dispatch() -> None:
    expanded = config("foobar", "second")

    assert not expanded.has_hidden_default


def test_multiple_commands_render_purpose_groups_before_globals() -> None:
    multi = cyclopts.App(name="example", help="Example commands.", help_format="plaintext")
    globals_group = cyclopts.Group("Global options", sort_key=100)
    multi["--help"].group = globals_group
    multi["--version"].group = globals_group

    @multi.command(group=cyclopts.Group("Core", sort_key=10))
    def foobar() -> None:
        """Run the core operation."""

    @multi.command(group=cyclopts.Group("Inspection", sort_key=20))
    def inspect() -> None:
        """Inspect data."""

    output = HelpSystem(multi, config("foobar", "inspect"))._render([], detailed=False, color=False)

    assert "Commands:\n  Core\N{EN DASH}" in output
    assert "\n  Inspection\N{EN DASH}" in output
    assert output.index("Commands:") < output.index("Global options:")


def test_forced_color_uses_stake_palette() -> None:
    output = HelpSystem(app, config(*COMMANDS))._render(["foobar"], detailed=False, color=True)

    assert "\x1b[" in output
    assert "\x1b[1;32m" in output
    assert "\x1b[1;36m" in output


def test_pager_resolution(monkeypatch) -> None:
    monkeypatch.setenv("PAGER", "less -FRX")
    pager = Pager.discover()

    assert pager is not None
    assert pager.argv == ("less", "-FRX")
    assert pager.supports_color


def test_invalid_pager_syntax_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("PAGER", "'unterminated")

    assert Pager.discover() is None
