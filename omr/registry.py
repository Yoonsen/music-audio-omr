"""Engine name -> class registry."""
from __future__ import annotations

from .base import OMREngine
from .engines import AudiverisEngine, HomrEngine

ENGINES: dict[str, type[OMREngine]] = {
    "audiveris": AudiverisEngine,
    "homr": HomrEngine,
}


def get_engine(name: str, **kwargs) -> OMREngine:
    try:
        cls = ENGINES[name]
    except KeyError:
        raise ValueError(f"Unknown OMR engine {name!r}. Available: {sorted(ENGINES)}") from None
    return cls(**kwargs)
