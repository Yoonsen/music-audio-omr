"""Input normalization.

Audiveris accepts PDFs directly. homr only accepts raster images, so a PDF
needs to be rasterized into per-page images first. This module keeps that
one piece of shared logic in one place.
"""
from __future__ import annotations

from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def is_pdf(path: Path) -> bool:
    return Path(path).suffix.lower() == ".pdf"


def pdf_to_page_images(pdf_path: Path, output_dir: Path, dpi: int = 300) -> list[Path]:
    """Rasterize each page of a PDF to a PNG file in output_dir.

    Requires the optional `pypdfium2` dependency (extra: "omr").
    """
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ImportError(
            "Rasterizing PDFs requires pypdfium2. Install it with "
            "`uv add pypdfium2` or `uv sync --extra omr`."
        ) from exc

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scale = dpi / 72
    pdf = pdfium.PdfDocument(str(pdf_path))
    out_paths = []
    try:
        for i, page in enumerate(pdf):
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            out_path = output_dir / f"{pdf_path.stem}-page-{i + 1:03d}.png"
            image.save(out_path)
            out_paths.append(out_path)
            page.close()
    finally:
        pdf.close()
    return out_paths


def ensure_image_inputs(input_path: Path, work_dir: Path, dpi: int = 300) -> list[Path]:
    """Return a list of raster image paths for `input_path`.

    If input_path is already an image, returns [input_path]. If it's a PDF,
    rasterizes every page into work_dir and returns those paths in order.
    """
    input_path = Path(input_path)
    if is_pdf(input_path):
        return pdf_to_page_images(input_path, work_dir, dpi=dpi)
    if input_path.suffix.lower() in IMAGE_SUFFIXES:
        return [input_path]
    raise ValueError(f"Unsupported input type: {input_path.suffix}")
