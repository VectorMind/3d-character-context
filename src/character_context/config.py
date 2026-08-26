"""Local configuration: `.env` loading, credentials, and YAML config.

The git-ignored `.env` at the repository root is the single local
configuration surface: it carries provider credentials (`HF_TOKEN`) and the
selected project folder (`CHARCTX_PROJECT`). Committed YAML under `config/`
declares endpoints, Space ids, and tool pins - never secrets.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .paths import ARTIFACTS_CONFIG, ENV_FILE, PROVIDERS_CONFIG

#: Name of the environment variable selecting the external project folder.
PROJECT_ENV_VAR = "CHARCTX_PROJECT"


class ConfigError(RuntimeError):
    """Configuration is missing or unusable, with a message naming the fix."""


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Load `KEY=VALUE` pairs from `.env` into the environment.

    Real environment variables win over the file, so a shell export or CI
    secret overrides local configuration. Returns what the file declared.
    """
    env_path = path or ENV_FILE
    declared: dict[str, str] = {}
    if not env_path.is_file():
        return declared
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        declared[key] = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, declared[key])
    return declared


def credential(name: str, *, required: bool = True) -> str | None:
    """Read a provider credential, naming the variable when it is missing."""
    load_dotenv()
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if not required:
        return None
    raise ConfigError(
        f"Missing credential {name}. Add `{name}=...` to {ENV_FILE} "
        f"or export {name} in the environment."
    )


def has_credential(name: str) -> bool:
    """True when a credential is available, without revealing it."""
    return credential(name, required=False) is not None


def mask(secret: str | None) -> str:
    """Render a credential safe to print or write into a report.

    Presence and length only: not one character of the value is shown, so no
    output of this program can leak a fragment of a credential.
    """
    if not secret:
        return "not set"
    return f"set ({len(secret)} chars)"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Missing configuration file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level.")
    return data


@lru_cache(maxsize=1)
def providers_config() -> dict[str, Any]:
    """`config/providers.yaml` - backend endpoints and call shapes."""
    return _load_yaml(PROVIDERS_CONFIG)


@lru_cache(maxsize=1)
def artifacts_config() -> dict[str, Any]:
    """`config/artifacts.yaml` - external tool pins."""
    return _load_yaml(ARTIFACTS_CONFIG)


def backend_config(name: str | None = None) -> tuple[str, dict[str, Any]]:
    """Resolve a backend name to its declared configuration.

    Passing `None` selects `default_backend`.
    """
    config = providers_config()
    backends = config.get("backends") or {}
    resolved = name or config.get("default_backend")
    if not resolved:
        raise ConfigError(
            f"No backend given and no `default_backend` in {PROVIDERS_CONFIG}."
        )
    if resolved not in backends:
        known = ", ".join(sorted(backends)) or "none"
        raise ConfigError(
            f"Unknown backend {resolved!r}. Configured backends: {known}. "
            f"Alternatives listed in {PROVIDERS_CONFIG} are documentation only."
        )
    return resolved, backends[resolved]


def artifact_config(name: str) -> dict[str, Any]:
    """Resolve an external tool name to its declared artifact entry."""
    artifacts = artifacts_config().get("artifacts") or {}
    if name not in artifacts:
        known = ", ".join(sorted(artifacts)) or "none"
        raise ConfigError(
            f"Unknown artifact {name!r}. Declared artifacts: {known} "
            f"(see {ARTIFACTS_CONFIG})."
        )
    return artifacts[name]
