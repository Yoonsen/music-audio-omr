"""omr: a small, uniform wrapper around external OMR engines.

Each engine reads an image (or, for Audiveris, a PDF) and produces a raw
symbolic hypothesis of its contents — nothing more:

- "audiveris": Audiveris (Java, external install) -> MusicXML (.mxl)
- "homr":      homr (uv-installable)               -> MusicXML

None of these is ground truth by itself; see `manifest.md` and
`architecture-manifest.md` for why this project treats OMR and audio as two
uncertain sources of evidence rather than a single pipeline to trust. This
module's job stops at producing per-engine hypotheses — lowering them into
positional bitmaps for the fusion pipeline is a separate, later step.
"""
from __future__ import annotations

from pathlib import Path

from .base import OMREngine, OMRError, OMRResult
from .io_utils import ensure_image_inputs
from .registry import ENGINES, get_engine

__all__ = [
    "OMREngine",
    "OMRError",
    "OMRResult",
    "ENGINES",
    "get_engine",
    "recognize",
]


def recognize(
    input_path: str | Path,
    engine: str = "audiveris",
    output_dir: str | Path = "omr_output",
    **engine_kwargs,
) -> list[OMRResult]:
    """Run one OMR engine on one input file (image or PDF).

    Returns one OMRResult per page. Audiveris consumes PDFs natively, so a
    multi-page PDF yields a single OMRResult for the whole book. homr only
    accepts raster images, so a PDF input is rasterized page by page first
    (see `io_utils.pdf_to_page_images`) and each page is run separately.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    eng = get_engine(engine, **engine_kwargs)

    if engine == "audiveris":
        return [eng.run(input_path, output_dir)]

    images = ensure_image_inputs(input_path, output_dir / "_pages")
    return [eng.run(image, output_dir) for image in images]
