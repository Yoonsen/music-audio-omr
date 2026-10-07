"""Render a MusicXML/.mxl OMR result to score PNG(s).

Uses Verovio (MusicXML -> SVG engraving) and `rsvg-convert` (SVG -> PNG).
This is a visual sanity check on an engine's output, not a claim that the
engraving is correct — see `manifest.md` for why OMR output should be
treated as a hypothesis, not ground truth. Garbled recognition (wrong
clefs, spurious accidentals, mis-tagged tremolos, ...) will render exactly
as garbled as the underlying MusicXML.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

try:
    import verovio
except ImportError:  # pragma: no cover - exercised via is_available()
    verovio = None

RSVG_CONVERT = "rsvg-convert"


class RenderError(RuntimeError):
    """Raised when rendering deps are missing or verovio can't load the score."""


def is_available() -> tuple[bool, str]:
    """Return (True, "") if score rendering can run, else (False, reason)."""
    if verovio is None:
        return False, (
            "verovio is not installed. Install it with `uv add verovio` "
            "(or `uv sync --extra omr-render`)."
        )
    if not shutil.which(RSVG_CONVERT):
        return False, (
            "rsvg-convert not found on PATH. Install it via your package "
            "manager, e.g. `apt install librsvg2-bin` / `brew install librsvg`."
        )
    return True, ""


def render_score_png(
    musicxml_path: str | Path,
    output_dir: str | Path,
    stem: str | None = None,
    page_width: int = 2100,
    scale: int = 40,
    keep_svg: bool = False,
) -> list[Path]:
    """Render a MusicXML or `.mxl` file to one white-background PNG per page.

    `stem` names the output file(s); defaults to `musicxml_path`'s stem.
    A single-page score writes `<stem>.png`; a multi-page score writes
    `<stem>_p1.png`, `<stem>_p2.png`, ... Returns the list of PNG paths
    written, in page order.
    """
    available, reason = is_available()
    if not available:
        raise RenderError(reason)

    musicxml_path = Path(musicxml_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or musicxml_path.stem

    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": page_width, "scale": scale, "adjustPageHeight": True})
    if not tk.loadFile(str(musicxml_path)):
        raise RenderError(f"verovio could not load {musicxml_path}")

    n_pages = tk.getPageCount()
    written: list[Path] = []
    for i in range(1, n_pages + 1):
        suffix = "" if n_pages == 1 else f"_p{i}"
        svg_path = output_dir / f"{stem}{suffix}.svg"
        png_path = output_dir / f"{stem}{suffix}.png"

        svg_path.write_text(tk.renderToSVG(i), encoding="utf-8")
        cmd = [
            RSVG_CONVERT,
            "-o", str(png_path),
            "-w", str(page_width),
            "--background-color=white",
            str(svg_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RenderError(f"rsvg-convert failed on {svg_path}: {proc.stderr}")

        if not keep_svg:
            svg_path.unlink()
        written.append(png_path)

    return written
