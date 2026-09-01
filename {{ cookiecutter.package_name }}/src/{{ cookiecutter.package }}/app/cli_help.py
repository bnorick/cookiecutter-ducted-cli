"""Stake-style concise and detailed help for Cyclopts applications."""

from __future__ import annotations

import io
import os
import shlex
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast, get_args

from rich.console import Console
from rich.text import Text

if TYPE_CHECKING:
    import cyclopts
    from cyclopts.help import HelpEntry, HelpPanel


HELP_STYLE = "bold green"
LITERAL_STYLE = "bold cyan"
PLACEHOLDER_STYLE = "cyan"


def _plain(value: Any, console: Console) -> str:
    """Render a Rich/Cyclopts value as unstyled text."""
    if value is None:
        return ""
    if hasattr(value, "plain"):
        return str(value.plain).rstrip()
    buffer = io.StringIO()
    plain_console = Console(file=buffer, width=console.width, no_color=True, highlight=False, markup=False)
    plain_console.print(value, end="")
    return buffer.getvalue().rstrip()


def _first_paragraph(value: str) -> str:
    return " ".join(value.split("\n\n", 1)[0].split())


def _is_bool(annotation: Any) -> bool:
    if annotation is bool:
        return True
    return bool(annotation is not None and bool in get_args(annotation) and type(None) in get_args(annotation))


def _placeholder(entry: HelpEntry) -> str | None:
    positional = next((name for name in entry.positive_names if not name.startswith("-")), None)
    has_option = any(name.startswith("-") for name in entry.all_options)
    if has_option and positional and not _is_bool(entry.type):
        return positional.replace("-", "_")
    return None


def _entry_name(entry: HelpEntry) -> tuple[str, bool]:
    positional = [name for name in entry.positive_names if not name.startswith("-")]
    options = [*entry.positive_shorts]
    options.extend(name for name in entry.positive_names if name.startswith("-"))
    options.extend(entry.negative_shorts)
    options.extend(entry.negative_names)
    if not options or (entry.required and positional):
        return (positional[0] if positional else "", True)
    name = ", ".join(options)
    if placeholder := _placeholder(entry):
        name += f" <{placeholder}>"
    return name, False


def _metadata(entry: HelpEntry) -> str:
    parts: list[str] = []
    if entry.choices:
        parts.append(f"[possible values: {', '.join(entry.choices)}]")
    if entry.default is not None and entry.default != "False":
        parts.append(f"[default: {entry.default}]")
    return " ".join(parts)


def _styled_name(name: str) -> Text:
    text = Text()
    if " <" in name and name.endswith(">"):
        literal, placeholder = name.rsplit(" ", 1)
        text.append(literal, style=LITERAL_STYLE)
        text.append(" ")
        text.append(placeholder, style=PLACEHOLDER_STYLE)
    else:
        text.append(name, style=LITERAL_STYLE)
    return text


class StakeHelpFormatter:
    """Classic aligned help formatter with concise and detailed modes."""

    def __init__(self, *, detailed: bool, usage: str) -> None:
        self.detailed = detailed
        self.usage = usage
        self._printed_commands_heading = False

    def render_usage(self, console: Console, options: Any, usage: Any) -> None:
        del options
        raw = _plain(usage, console).removeprefix("Usage:").strip()
        suffix = raw[raw.find("[OPTIONS]") :] if "[OPTIONS]" in raw else "[OPTIONS]"
        suffix = suffix.replace(" [ARGS]", "")
        if self.usage.endswith(" help"):
            suffix = suffix.replace("[ARGS...]", "[COMMAND]...")
        usage = f"{self.usage} {suffix}"
        console.print(Text.assemble(("Usage:", HELP_STYLE), " ", (usage, LITERAL_STYLE)))
        console.print()

    def render_description(self, console: Console, options: Any, description: Any) -> None:
        del options
        text = _plain(description, console)
        if not text:
            return
        text = text if self.detailed else _first_paragraph(text)
        console.print(text, highlight=False)
        console.print()

    def __call__(self, console: Console, options: Any, panel: HelpPanel) -> None:
        del options
        if not panel.entries:
            return
        if panel.format == "command":
            if str(panel.title).casefold() == "global options":
                self._render_entries(console, "Global options", panel.entries)
            else:
                self._render_commands(console, panel)
            return

        arguments: list[HelpEntry] = []
        options: list[HelpEntry] = []
        for entry in panel.entries:
            _, positional = _entry_name(entry)
            (arguments if positional else options).append(entry)

        title = str(panel.title)
        if arguments:
            self._render_entries(console, "Arguments", arguments)
        if options:
            heading = "Global options" if title.casefold() == "global options" else "Options"
            self._render_entries(console, heading, options)

    def _render_commands(self, console: Console, panel: HelpPanel) -> None:
        if not self._printed_commands_heading:
            console.print(Text("Commands:", style=HELP_STYLE))
            self._printed_commands_heading = True
        title = str(panel.title)
        if title.casefold() != "commands":
            console.print(Text.assemble("  ", (f"{title}\N{EN DASH}", HELP_STYLE)))
            indent = 4
        else:
            indent = 2
        width = max(len(_entry_name(entry)[0]) for entry in panel.entries)
        for entry in panel.entries:
            name, _ = _entry_name(entry)
            desc = _first_paragraph(_plain(entry.description, console))
            line = Text(" " * indent)
            line.append_text(_styled_name(name))
            line.append(" " * (width - len(name)))
            if desc:
                line.append(f"  {desc}")
            console.print(line, highlight=False)
        console.print()

    def _render_entries(self, console: Console, heading: str, entries: list[HelpEntry]) -> None:
        console.print(Text(f"{heading}:", style=HELP_STYLE))
        names = [_entry_name(entry)[0] for entry in entries]
        width_names = list(names)
        has_help = any("--help" in entry.all_options for entry in entries)
        if heading == "Global options" and not has_help:
            width_names.append("-h, --help")
        width = max(len(name) for name in width_names)
        for entry, name in zip(entries, names, strict=True):
            description = _plain(entry.description, console)
            metadata = _metadata(entry)
            if self.detailed:
                self._render_detailed_entry(console, name, description, metadata)
            else:
                self._render_concise_entry(console, name, width, description, metadata)
        if heading == "Global options" and not has_help:
            self._render_help_entry(console, width)
        console.print()

    def _render_detailed_entry(self, console: Console, name: str, description: str, metadata: str) -> None:
        console.print(Text.assemble("  ", _styled_name(name)))
        body = description
        if metadata:
            body = f"{body}\n\n{metadata}" if body else metadata
        for paragraph in (part for part in body.split("\n\n") if part.strip()):
            console.print()
            console.print(
                textwrap.fill(
                    " ".join(paragraph.split()),
                    width=console.width,
                    initial_indent="          ",
                    subsequent_indent="          ",
                ),
                highlight=False,
            )

    @staticmethod
    def _render_concise_entry(
        console: Console,
        name: str,
        width: int,
        description: str,
        metadata: str,
    ) -> None:
        description = _first_paragraph(description)
        suffix = " ".join(part for part in (description, metadata) if part)
        wrapped = textwrap.wrap(suffix, width=max(20, console.width - width - 4)) or [""]
        for index, part in enumerate(wrapped):
            line = Text("  ")
            if index == 0:
                line.append_text(_styled_name(name))
                line.append(" " * (width - len(name)))
            else:
                line.append(" " * width)
            if part:
                line.append(f"  {part}")
            console.print(line, highlight=False)

    def _render_help_entry(self, console: Console, width: int) -> None:
        description = (
            "Display concise help for this command. Use "
            f"`{self.usage.split()[0]} help COMMAND` for detailed documentation."
        )
        if self.detailed:
            self._render_detailed_entry(console, "-h, --help", description, "")
        else:
            self._render_concise_entry(
                console,
                "-h, --help",
                width,
                "Display concise help for this command.",
                "",
            )


@dataclass(frozen=True)
class HelpConfig:
    """Public help behavior for one CLI."""

    program: str
    default_command: str
    operational_commands: tuple[str, ...]

    @property
    def has_hidden_default(self) -> bool:
        return len(self.operational_commands) == 1


class HelpConfigError(ValueError):
    """Raised when command registration and help configuration diverge."""

    @classmethod
    def default_not_operational(cls) -> HelpConfigError:
        return cls("the default command must be operational")

    @classmethod
    def coverage(cls, registered: set[str], configured: set[str]) -> HelpConfigError:
        return cls(f"help command coverage differs: registered={registered}, configured={configured}")

    @classmethod
    def purpose_group(cls, name: str) -> HelpConfigError:
        return cls(f"operational command `{name}` must have exactly one purpose group")


@dataclass(frozen=True)
class Pager:
    argv: tuple[str, ...]

    @classmethod
    def discover(cls) -> Pager | None:
        configured = os.environ.get("PAGER", "")
        if configured:
            try:
                argv = tuple(shlex.split(configured))
            except ValueError:
                return None
            return cls(argv) if argv else None
        for name in ("less", "more"):
            if path := shutil.which(name):
                return cls((path,))
        return None

    @property
    def supports_color(self) -> bool:
        return Path(self.argv[0]).name == "less" and (
            len(self.argv) == 1 or any(arg == "-R" or "R" in arg.lstrip("-") for arg in self.argv[1:])
        )

    def command(self) -> tuple[str, ...]:
        if Path(self.argv[0]).name == "less" and len(self.argv) == 1:
            return (*self.argv, "-R")
        return self.argv


class HelpSystem:
    """Route CLI help requests and normalize a single hidden default command."""

    def __init__(self, app: cyclopts.App, config: HelpConfig) -> None:
        self.app = app
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if self.config.default_command not in self.config.operational_commands:
            raise HelpConfigError.default_not_operational()
        help_app = next(
            (command for name, command in self.app._registered_commands.items() if name == "help"),
            None,
        )
        registered = {
            command.name[0]
            for command in self.app._registered_commands.values()
            if command.show and command.name and command is not help_app
        }
        expected = set(self.config.operational_commands)
        if registered != expected:
            raise HelpConfigError.coverage(registered, expected)
        for name in self.config.operational_commands:
            raw_groups = self.app[name].group
            groups = raw_groups if isinstance(raw_groups, tuple) else (raw_groups,)
            group_names = tuple(group if isinstance(group, str) else str(cast(Any, group).name) for group in groups)
            if len(group_names) != 1 or group_names[0].casefold() == "commands":
                raise HelpConfigError.purpose_group(name)

    def run(self, argv: Iterable[str]) -> list[str] | None:
        """Handle help and return normalized execution arguments otherwise."""
        args = list(argv)
        if args and args[0] == "help":
            self._run_detailed(args[1:])
            return None
        if any(arg in {"-h", "--help"} for arg in args):
            help_index = next(i for i, arg in enumerate(args) if arg in {"-h", "--help"})
            self._write(self._render(self._command_path(args[:help_index]), detailed=False))
            return None
        return self.normalize(args)

    def normalize(self, args: list[str]) -> list[str]:
        if not self.config.has_hidden_default:
            return args
        if args and args[0] in self.config.operational_commands:
            return args
        return [self.config.default_command, *args]

    def _command_path(self, prefix: list[str]) -> list[str]:
        if prefix and prefix[0] in self.config.operational_commands:
            return [prefix[0]]
        return [self.config.default_command] if self.config.has_hidden_default else []

    def _run_detailed(self, args: list[str]) -> None:
        if any(arg in {"-h", "--help"} for arg in args):
            self._write(self._render(["help"], detailed=False))
            return
        no_pager = False
        path: list[str] = []
        for arg in args:
            if arg == "--no-pager":
                no_pager = True
            elif arg.startswith("-"):
                self._fail(f"unexpected help option `{arg}`")
            else:
                path.append(arg)
        if not path:
            path = [self.config.default_command] if self.config.has_hidden_default else []
        output = self._render(path, detailed=bool(path))
        if path and not no_pager and sys.stdout.isatty() and (pager := Pager.discover()):
            self._page(pager, path)
        else:
            self._write(output)

    def _render(self, path: list[str], *, detailed: bool, color: bool | None = None) -> str:
        self._validate_path(path)
        width = max(40, shutil.get_terminal_size((100, 24)).columns)
        usage_path = [] if self.config.has_hidden_default and path == [self.config.default_command] else path
        usage = " ".join((self.config.program, *usage_path))
        formatter = StakeHelpFormatter(detailed=detailed, usage=usage)
        buffer = io.StringIO()
        if color is None:
            color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        console = Console(
            file=buffer,
            width=width,
            force_terminal=color,
            color_system="standard" if color else None,
            no_color=not color,
            highlight=False,
            markup=False,
        )
        previous = self.app.help_formatter
        self.app.help_formatter = formatter
        try:
            self.app.help_print(path, console=console)
        finally:
            self.app.help_formatter = previous
        output = buffer.getvalue().rstrip() + "\n"
        if not detailed and path:
            output += f"\nUse `{self.config.program} help {' '.join(path)}` for more details.\n"
        return output

    def _validate_path(self, path: list[str]) -> None:
        if not path:
            return
        command_chain, _, _ = self.app.parse_commands(path)
        if list(command_chain) != path:
            self._fail(f"there is no command `{' '.join(path)}` for `{self.config.program}`")

    def _page(self, pager: Pager, path: list[str]) -> None:
        output = self._render(path, detailed=True, color=pager.supports_color)
        try:
            completed = subprocess.run(  # noqa: S603 - argv is executed directly without a shell.
                pager.command(), input=output, text=True, check=False
            )
        except FileNotFoundError as error:
            self._fail(f"failed to start pager `{pager.argv[0]}`: {error}")
        if completed.returncode not in {0, 141}:
            self._fail(f"pager exited with status {completed.returncode}")

    @staticmethod
    def _write(output: str) -> None:
        sys.stdout.write(output)

    @staticmethod
    def _fail(message: str) -> None:
        sys.stderr.write(f"error: {message}\n")
        raise SystemExit(2)
