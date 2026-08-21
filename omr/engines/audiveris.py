"""Wrapper around the Audiveris CLI (batch mode).

Audiveris is a Java application, not a Python package, so it is not
installed via pip/uv. Install it separately — a packaged release, or build
from source with Gradle:
https://github.com/Audiveris/audiveris

Point this wrapper at the executable via the AUDIVERIS_BIN environment
variable, or the `binary` constructor argument.

Audiveris accepts image files *and* multi-page PDFs directly, and exports
MusicXML packaged as a compressed `.mxl` file (`-export` implies
`-transcribe`). Reference:
https://audiveris.github.io/audiveris/_pages/guides/advanced/cli/
"""
from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from ..base import OMREngine, OMRError, OMRResult

DEFAULT_BINARY_NAMES = ("Audiveris", "audiveris")


class AudiverisEngine(OMREngine):
    name = "audiveris"
    output_format = "musicxml"

    def __init__(self, binary: str | None = None, timeout: float | None = 600):
        raw_binary = binary or os.environ.get("AUDIVERIS_BIN")
        self.binary = os.path.expanduser(raw_binary) if raw_binary else None
        self.timeout = timeout

    def _resolve_binary(self) -> str | None:
        if self.binary:
            return self.binary
        for candidate in DEFAULT_BINARY_NAMES:
            found = shutil.which(candidate)
            if found:
                return found
        return None

    def is_available(self) -> tuple[bool, str]:
        binary = self._resolve_binary()
        if not binary:
            return False, (
                "Audiveris executable not found. Install it from "
                "https://github.com/Audiveris/audiveris/releases (or build "
                "with Gradle), then set AUDIVERIS_BIN or pass binary=... "
                "explicitly."
            )
        return True, ""

    def run(self, input_path: Path, output_dir: Path) -> OMRResult:
        available, reason = self.is_available()
        if not available:
            raise OMRError(reason)

        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._resolve_binary(),
            "-batch",
            "-export",
            "-output", str(output_dir),
            str(input_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)

        output_path = self._find_output(output_dir, input_path.stem)
        success = proc.returncode == 0 and output_path is not None

        text = None
        if output_path and output_path.suffix == ".mxl":
            text = self._read_mxl_text(output_path)
        elif output_path:
            text = output_path.read_text(encoding="utf-8", errors="replace")

        return OMRResult(
            engine=self.name,
            input_path=input_path,
            output_format=self.output_format,
            success=success,
            output_path=output_path,
            text=text,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    @staticmethod
    def _find_output(output_dir: Path, stem: str) -> Path | None:
        for ext in (".mxl", ".xml"):
            candidates = sorted(output_dir.glob(f"{stem}*{ext}"))
            if candidates:
                return candidates[0]
        return None

    @staticmethod
    def _read_mxl_text(mxl_path: Path) -> str | None:
        """`.mxl` is a zip container around one MusicXML file; unwrap it."""
        try:
            with zipfile.ZipFile(mxl_path) as zf:
                names = [
                    n for n in zf.namelist()
                    if n.endswith(".xml") and "META-INF" not in n
                ]
                if not names:
                    return None
                return zf.read(names[0]).decode("utf-8")
        except (zipfile.BadZipFile, KeyError):
            return None
