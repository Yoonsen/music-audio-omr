"""Common types and interfaces shared by all OMR engine wrappers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


class OMRError(RuntimeError):
    """Raised when an engine is missing, misconfigured, or fails to run."""


@dataclass
class OMRResult:
    """Outcome of running one OMR engine on one input page/image.

    This is a raw hypothesis from a single external tool, not a final
    answer — see `manifest.md` for why none of the three engines should be
    treated as ground truth on its own.
    """

    engine: str
    input_path: Path
    output_format: str
    success: bool
    output_path: Path | None = None
    text: str | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    extra: dict = field(default_factory=dict)


class OMREngine(ABC):
    """Base class for a wrapped external OMR tool."""

    name: str
    output_format: str

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Return (True, "") if the engine can run, else (False, reason)."""

    @abstractmethod
    def run(self, input_path: Path, output_dir: Path) -> OMRResult:
        """Run the engine on a single raster image (or, for Audiveris, a PDF)."""
