"""Configuration rules: `.env` carries secrets and selection, committed YAML
carries endpoints and pins - and never the other way round."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from character_context import config
from character_context.config import ConfigError
from character_context.paths import ARTIFACTS_CONFIG, PROVIDERS_CONFIG


def test_dotenv_does_not_override_the_real_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HF_TOKEN=from-file\nOTHER=from-file\n", encoding="utf-8")
    monkeypatch.setenv("HF_TOKEN", "from-shell")
    monkeypatch.delenv("OTHER", raising=False)

    declared = config.load_dotenv(env_file)

    assert declared["HF_TOKEN"] == "from-file"
    assert config.credential("HF_TOKEN") == "from-shell"


def test_dotenv_ignores_comments_and_blanks(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n\nQUOTED=\"spaced value\"\nBARE=plain\nnot-a-pair\n",
        encoding="utf-8",
    )
    declared = config.load_dotenv(env_file)
    assert declared == {"QUOTED": "spaced value", "BARE": "plain"}


def test_missing_credential_names_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHARCTX_TEST_TOKEN", "")
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: {})
    with pytest.raises(ConfigError, match="CHARCTX_TEST_TOKEN"):
        config.credential("CHARCTX_TEST_TOKEN")
    assert config.credential("CHARCTX_TEST_TOKEN", required=False) is None


def test_mask_never_reveals_a_secret() -> None:
    secret = "hf_abcdefghijklmnopqrstuvwxyz"
    masked = config.mask(secret)
    # Not a single character of the value may appear, only its shape.
    assert masked == f"set ({len(secret)} chars)"
    for start in range(len(secret) - 3):
        assert secret[start : start + 4] not in masked
    assert config.mask(None) == "not set"


def test_committed_config_holds_no_secrets() -> None:
    """Config may name a credential variable; it must never carry its value."""
    secret_shaped = re.compile(
        r"(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{16,}|"
        r"(?i:api_key|password|secret)\s*:\s*\S+)"
    )
    for path in (PROVIDERS_CONFIG, ARTIFACTS_CONFIG):
        text = path.read_text(encoding="utf-8")
        found = secret_shaped.search(text)
        assert not found, f"{path} appears to carry a credential: {found}"
        # Naming the variable is exactly how a credential should be declared.
        assert "credential: HF_TOKEN" in PROVIDERS_CONFIG.read_text(encoding="utf-8")


def test_default_backend_resolves() -> None:
    name, entry = config.backend_config(None)
    assert name == "trellis2"
    assert entry["space"] == "microsoft/TRELLIS.2"
    assert entry["credential"] == "HF_TOKEN"


def test_unknown_backend_lists_the_known_ones() -> None:
    with pytest.raises(ConfigError) as excinfo:
        config.backend_config("meshy")
    assert "trellis2" in str(excinfo.value)


def test_alternatives_are_not_selectable_backends() -> None:
    # Documented alternatives must not be reachable as if they were coded.
    alternatives = config.providers_config().get("alternatives") or {}
    assert alternatives, "providers.yaml should document alternatives"
    for name in alternatives:
        with pytest.raises(ConfigError):
            config.backend_config(name)


def test_artifact_pin_is_exact() -> None:
    entry = config.artifact_config("blender")
    assert entry["version"] == "5.2.1"
    assert entry["version"] in entry["url"]
    assert len(entry["sha256"]) == 64
    assert "latest" not in entry["url"]


def test_unknown_artifact_lists_the_known_ones() -> None:
    with pytest.raises(ConfigError, match="blender"):
        config.artifact_config("houdini")
