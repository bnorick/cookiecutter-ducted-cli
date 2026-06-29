"""Configuration management with layered precedence.

Provides :class:`Config` for TOML file loading and :class:`ValueResolver` for
resolving values across environment variables, command-line arguments, and
config files.

Precedence order (highest to lowest):
1. Environment variables ({{ cookiecutter.env_var_prefix }}_*)
2. Command-line arguments
3. TOML configuration files (.local.toml > .toml)
4. Hardcoded defaults
"""

from __future__ import annotations

import builtins
import collections.abc
import dataclasses
import functools
import json
import os
import pathlib
import re
import tomllib
from typing import Any

import log


def load_config_safe(config_dir: Any = None) -> Config | None:
    """Try to load Config, return None if unavailable (no config dir, missing files, etc.)."""
    try:
        return Config.load(config_dir=config_dir)
    except (ValueError, FileNotFoundError) as e:
        log.debug(f"Config not loaded: {e}")
        return None


def split_toml_dotted_key(dotted_key: str) -> list[str]:
    """Split a TOML dotted key into its individual parts.

    Handles both bare keys and quoted keys.

    Args:
        dotted_key: The TOML dotted key as a string
            (e.g., ``"{{ cookiecutter.package_name }}.start.image"``).

    Returns:
        List of individual key parts.

    Example:
        >>> split_toml_dotted_key("{{ cookiecutter.package_name }}.start.image")
        ['{{ cookiecutter.package_name }}', 'start', 'image']
    """
    bare_key = r"[A-Za-z0-9_-]+"
    quoted_key = r"\"(?:[^\"]|\\\")*\"|'(?:[^']|\\')*'"
    key_pattern = rf"({bare_key}|{quoted_key})"
    keys = re.findall(key_pattern, dotted_key)
    return [k[1:-1] if k.startswith(("'", '"')) else k for k in keys]


def update_config(target: dict, source: dict, missing_only: bool = True) -> dict:
    """Recursively update *target* dict with *source* dict.

    Args:
        target: Dictionary to update.
        source: Dictionary to merge from.
        missing_only: If ``True``, only add keys that don't exist in *target*.

    Returns:
        Updated *target* dictionary.
    """
    for k, v in source.items():
        if isinstance(v, collections.abc.Mapping):
            target[k] = update_config(target.get(k, {}), dict(v), missing_only=missing_only)
        elif k not in target or not missing_only:
            target[k] = v
    return target


# ---------------------------------------------------------------------------
# Config - TOML loader
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Config:
    """TOML configuration loader with precedence support.

    Attributes:
        paths: Tuple of paths that were loaded (in load order).
        _config_dict: The merged configuration dictionary.
    """

    paths: tuple[pathlib.Path, ...]
    _config_dict: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a nested config value using dotted key notation.

        Args:
            key: Dotted key path
                (e.g., ``"{{ cookiecutter.package_name }}.start.image"``).
            default: Value to return when the key is missing.

        Returns:
            The configuration value or *default* if missing.
        """
        key_parts = split_toml_dotted_key(key)
        result: Any = self._config_dict
        for part in key_parts:
            if not isinstance(result, dict):
                return default
            result = result.get(part)
            if result is None:
                return default
        return result

    @classmethod
    @functools.cache
    def load(
        cls,
        config_dir: pathlib.Path | str | None = None,
        cluster_name: str | None = None,
    ) -> Config:
        """Load configuration from TOML files.

        Loads in priority order (higher priority first):
        1. ``{cluster}.local.toml`` (highest priority)
        2. ``{cluster}.toml``

        Missing keys in higher-priority configs are filled from lower priority.

        Args:
            config_dir: Directory containing config files.  If ``None``, uses
                the ``{{ cookiecutter.env_var_prefix }}_CONFIG_DIR`` env var.
            cluster_name: Cluster name for config files.  If ``None``, uses
                the ``CLUSTER_NAME`` env var.

        Returns:
            Config object with merged configuration.

        Raises:
            ValueError: If config_dir or cluster_name cannot be resolved.
            FileNotFoundError: If no config files are found.
        """
        if config_dir is None:
            config_dir = os.getenv("{{ cookiecutter.env_var_prefix }}_CONFIG_DIR")
            if not config_dir:
                raise ValueError(
                    "config_dir must be provided or {{ cookiecutter.env_var_prefix }}_CONFIG_DIR environment variable must be set"
                )

        if cluster_name is None:
            cluster_name = os.getenv("CLUSTER_NAME")
            if not cluster_name:
                raise ValueError("cluster_name must be provided or CLUSTER_NAME environment variable must be set")

        config_dir = pathlib.Path(config_dir).expanduser().resolve()

        candidate_paths = [
            config_dir / f"{cluster_name.lower()}.local.toml",
            config_dir / f"{cluster_name.lower()}.toml",
        ]

        if not any(p.exists() for p in candidate_paths):
            raise FileNotFoundError(
                "Unable to load configuration, cannot find config at any of the following paths:\n  "
                + "\n  ".join(str(p) for p in candidate_paths)
            )

        loaded_paths: list[pathlib.Path] = []
        config_dict: dict[str, Any] | None = None

        for path in candidate_paths:
            if not path.exists():
                continue
            content = tomllib.loads(path.read_text())
            if config_dict is None:
                config_dict = content
            else:
                update_config(config_dict, content, missing_only=True)
            loaded_paths.append(path)

        if config_dict is None:
            raise FileNotFoundError(
                "Unable to load configuration, cannot find config at any of the following paths:\n  "
                + "\n  ".join(str(p) for p in candidate_paths)
            )

        log.debug(f"Loaded config from: {', '.join(str(p) for p in loaded_paths)}")
        return cls(paths=tuple(loaded_paths), _config_dict=config_dict)


# ---------------------------------------------------------------------------
# ValueResolver - env > args > config > default
# ---------------------------------------------------------------------------


def _coerce_from_env(value: str, target_type: builtins.type) -> Any:
    """Coerce an env-var string to the given type."""
    if target_type is bool:
        return value.lower() in ("1", "true", "yes", "on")
    if target_type in (int, float):
        return target_type(value)
    if target_type is list:
        return json.loads(value)
    return value


class _NOT_SET_TYPE:
    pass


NOT_SET = _NOT_SET_TYPE()


class _MISSING_TYPE:
    pass


MISSING = _MISSING_TYPE()


@dataclasses.dataclass
class ValueResolver:
    """Unified value resolution across environment, arguments, and config.

    Implements precedence: **env** > **args** > **config** > **default**.

    Attributes:
        args: Dictionary of command-line arguments.
        config: Config object (may be ``None`` if not loaded).
    """

    args: dict[str, Any]
    config: Config | None = None

    def get(
        self,
        env: str | None = None,
        arg: str | None = None,
        config: str | None = None,
        default: Any = NOT_SET,
        required: bool = True,
        desc: str = "",
        type: builtins.type | None = None,  # noqa: A002
    ) -> Any:
        """Resolve a value using priority: env > arg > config > default.

        Resolution proceeds through each source in order and returns the first
        non-None value.  If all sources yield None, raises ``ValueError`` when
        *required* is ``True``, otherwise returns ``None``.

        Env-var strings are coerced to the target type.  The target type is
        determined in order: explicit *type* argument > type of *default*
        (when not None/NOT_SET) > no coercion (string returned as-is).

        Args:
            env: Environment variable name to check.
            arg: Argument key in *args* dict.
            config: Config dotted key to look up.
            default: Fallback value.  Use :data:`NOT_SET` for "no default".
            required: If ``True``, raise when no source yields a value.
            desc: Human-readable name for error messages.
            type: Explicit target type for env-var coercion.

        Returns:
            First non-None resolved value.

        Raises:
            ValueError: If *required* is ``True`` and all sources yield None.
        """
        target_type = type or (builtins.type(default) if default not in (NOT_SET, None) else None)

        # 1. Environment
        if env:
            value = os.getenv(env)
            if value is not None:
                if target_type is not None:
                    value = _coerce_from_env(value, target_type)
                log.debug(f"Resolved {desc or env} from environment: {value}")
                return value

        # 2. Arguments
        if arg:
            value = self.args.get(arg, MISSING)
            if value is not MISSING and value is not None:
                log.debug(f"Resolved {desc or arg} from arguments: {value}")
                return value

        # 3. Config
        if config and self.config:
            value = self.config.get(config)
            if value is not None:
                log.debug(f"Resolved {desc or config} from config: {value}")
                return value

        # 4. Default
        if default is not NOT_SET:
            log.debug(f"Resolved {desc or 'value'} from default: {default}")
            return default

        # 5. Error if required
        if required:
            sources = []
            if env:
                sources.append(f"environment variable {env!r}")
            if arg:
                sources.append(f"argument {arg!r}")
            if config:
                sources.append(f"config key [{config!r}]")
            sources_str = " or ".join(sources)
            desc_str = f" for {desc}" if desc else ""
            raise ValueError(f"Unable to resolve value{desc_str} from {sources_str}")

        return None


# Backward-compatibility alias
Context = ValueResolver
