"""Hosted generator backends.

There is deliberately no protocol class and no registry here. The image-to-3d
API landscape is not settled enough to abstract: real backends differ in
staging (single call vs session-stateful vs poll-a-job), in options, and in
what they return. Abstracting that now would encode one backend's shape as if
it were the general one.

What is shared is the contract, not the machinery: a backend module exposes

    generate(request: GenerationRequest, ...) -> RawCharacterResult

and keeps every provider-native response inside itself. When a second backend
actually lands in code, the then-known shape of two real backends can drive
whatever abstraction is warranted.
"""

from __future__ import annotations

from types import ModuleType

from ..config import ConfigError

#: Backend keys in `config/providers.yaml` that have code behind them.
IMPLEMENTED = ("trellis2",)


def resolve(name: str) -> ModuleType:
    """Import the module implementing a configured backend key."""
    if name == "trellis2":
        from . import trellis2

        return trellis2
    raise ConfigError(
        f"Backend {name!r} is configured but not implemented. "
        f"Implemented backends: {', '.join(IMPLEMENTED)}. Entries under "
        "`alternatives:` in config/providers.yaml are documentation only."
    )
