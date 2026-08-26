"""3d-character-context: generative-first 3D character workbench.

Two surfaces, by rule:

- the documented `charctx` CLI, the single interface for humans and agents;
- this Python API, which is side-effect-free - it returns data and in-memory
  objects, and never writes files. Producing artifacts is an explicit act
  through the CLI or through the named write/fetch functions.
"""

from __future__ import annotations

from .contracts import (
    CanonicalizationResult,
    GenerationRequest,
    MeshMeasurements,
    RawCharacterResult,
    RiggedCharacterResult,
)
from .mesh_report import measure

__version__ = "0.1.0"

__all__ = [
    "CanonicalizationResult",
    "GenerationRequest",
    "MeshMeasurements",
    "RawCharacterResult",
    "RiggedCharacterResult",
    "__version__",
    "measure",
]
