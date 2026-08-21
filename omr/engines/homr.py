"""Wrapper around the `homr` CLI (https://github.com/liebharc/homr).

Install with `uv add homr`, or run ad hoc with `uvx homr` (CPU only). homr
writes a MusicXML file next to the input image
rather than accepting an output path, and its exact output filename isn't
documented, so this wrapper snapshots the input's directory before and
after running and treats any newly created MusicXML-like file as the
result, then copies it into the requested output directory.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from ..base import OMREngine, OMRError, OMRResult

OUTPUT_SUFFIXES = {".musicxml", ".xml", ".mxl"}


class HomrEngine(OMREngine):
    name = "homr"
    output_format = "musicxml"

    def __init__(self, timeout: float | None = 900):
        self.timeout = timeout

    def is_available(self) -> tuple[bool, str]:
        if shutil.which("homr"):
            return True, ""
        try:
            import homr  # noqa: F401
        except ImportError:
            return False, (
                "homr is not installed. Install it with `uv add homr` "
                "(see https://github.com/liebharc/homr)."
            )
        return True, ""

    def run(self, input_path: Path, output_dir: Path) -> OMRResult:
        available, reason = self.is_available()
        if not available:
            raise OMRError(reason)

        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        binary = shutil.which("homr")
        cmd = [binary, str(input_path)] if binary else [sys.executable, "-m", "homr", str(input_path)]

        input_dir = input_path.parent
        before = set(input_dir.iterdir())
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        after = set(input_dir.iterdir())

        new_files = sorted(
            p for p in (after - before) if p.suffix.lower() in OUTPUT_SUFFIXES
        )
        produced = new_files[0] if new_files else None
        if produced is None:
            # Fall back for reruns where the output already existed.
            for ext in (".musicxml", ".xml"):
                guess = input_path.with_suffix(ext)
                if guess.exists():
                    produced = guess
                    break

        output_path = None
        if produced is not None:
            output_path = output_dir / produced.name
            shutil.copy2(produced, output_path)

        return OMRResult(
            engine=self.name,
            input_path=input_path,
            output_format=self.output_format,
            success=proc.returncode == 0 and output_path is not None,
            output_path=output_path,
            text=output_path.read_text(encoding="utf-8", errors="replace") if output_path else None,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
