# Music Audio OMR

This is an early research notebook project for connecting optical music
recognition (OMR) with audio evidence through positional indexes.

The mathematical background is in `type-lowering.pdf`: instead of imagining a
"raised" CPU, data is lowered into positional indicator fields or bitmaps, where
ordinary bitwise operations can do useful parallel work.

## Current Status

- `manifest.md` is the current project manifesto and should be read first.
- `idea-manifest.md` is the earlier raw note and sketch.
- `notebooks/01_omr_probe.ipynb` is the first practical experiment.
- `page-000.png` is the current test image for the notebook.

The first notebook does not try to recognize notes. It probes whether simple
OpenCV operations can extract staff-line evidence from a page image.

## Setup

This repo currently uses `uv`.

```bash
uv sync
```

To verify that OpenCV is available:

```bash
uv run python -c "import cv2; print(cv2.__version__)"
```

Then open `notebooks/01_omr_probe.ipynb` in Jupyter or Cursor and run it against
`page-000.png`.

## Next Step

The horizontal evidence in the first probe looked promising. The next small
step is to turn the detected horizontal structures into explicit staff-line
bands and then group them into five-line staff systems.
