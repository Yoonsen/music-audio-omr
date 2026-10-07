# omr

A thin wrapper around external OMR (Optical Music Recognition) engines.
Each one turns an image or PDF into a symbolic hypothesis.

Currently this module wraps two OMR engines: Audiveris and homr. The idea
behind wrapping more than one is to understand how they behave differently,
and whether combining their output gives a more informed result than either
alone.

| engine      | install                                  | input           | output              |
|-------------|-------------------------------------------|-----------------|----------------------|
| `audiveris` | external Java app, not uv/pip-installable | image or PDF    | MusicXML (`.mxl`)   |
| `homr`      | `uv add homr`                             | image only      | MusicXML            |

## Usage

```python
from omr import recognize

results = recognize("page-000.png", engine="homr", output_dir="omr_output")
for r in results:
    print(r.engine, r.success, r.output_path)
```

or from the command line:

```bash
python -m omr homr page-000.png -o omr_output
python -m omr audiveris score.pdf -o omr_output --audiveris-bin /opt/audiveris/bin/Audiveris
```

Add `--score-png` to also engrave each successful result's MusicXML back to a
PNG (via Verovio + `rsvg-convert`), written next to the MusicXML/`.mxl`
output as `<stem>.png` (or `<stem>_p1.png`, `<stem>_p2.png`, ... for a
multi-page score):

```bash
python -m omr audiveris score.pdf -o omr_output/audiveris --score-png
```

This is a visual sanity check on the raw OMR output, not a corrected score —
whatever the engine misread (wrong clef, spurious accidental, ...) renders
exactly as misread. See `omr/render.py`; from Python:

```python
from omr.render import render_score_png

png_paths = render_score_png("omr_output/audiveris/score.mxl", "omr_output/audiveris")
```

Needs the `omr-render` extra (`uv sync --extra omr-render`) plus
`rsvg-convert` on PATH (`apt install librsvg2-bin` / `brew install librsvg`
— not pip-installable, so it's not part of the extra).

A PDF input is passed to Audiveris as-is (it handles multi-page books
natively). For `homr`, which only accepts raster images, a PDF is first
rasterized page by page (via the optional `pypdfium2` dependency, installed
with `uv sync --extra omr`) into `<output_dir>/_pages/`, and each page is
run separately — so you get back a list of `OMRResult`, one per page.

## Setting up each engine

### Audiveris

Audiveris is a Java desktop application, not a Python package — installing
it is a one-time, separate step:

1. Download a packaged release from
   [github.com/Audiveris/audiveris/releases](https://github.com/Audiveris/audiveris/releases),
   or build from source with Gradle.
2. Point this module at the executable, either:
   - `export AUDIVERIS_BIN=/path/to/Audiveris`, or
   - `AudiverisEngine(binary="/path/to/Audiveris")` / `--audiveris-bin` on the CLI.

Under the hood this runs `Audiveris -batch -export -output <dir> <input>`,
which transcribes and exports MusicXML packaged as a compressed `.mxl`
file. Reference:
[CLI docs](https://audiveris.github.io/audiveris/_pages/guides/advanced/cli/).

### homr

A regular uv-installable package:

```bash
uv sync --extra omr-homr   # adds it to this project's environment, or:
uv add homr                # equivalent, writes it into pyproject.toml directly
# or, ad hoc, no install:
uvx homr page-000.png
```

[github.com/liebharc/homr](https://github.com/liebharc/homr) — AGPL-3.0
licensed. It writes its MusicXML output next to the input image rather
than to a chosen output path. This wrapper detects the new file and copies
it into `output_dir` for you.

If you also need PDF input rasterized for homr, sync both extras at once:
`uv sync --extra omr --extra omr-homr`.

## Confidence / logits

Neither engine reports confidence in its MusicXML, but both have it internally:

- **Audiveris** saves a `grade` and `ctx-grade` (0–1) for every symbol in its
  `.omr` project file, a zip archive with `sheet#N/sheet#N.xml` inside. No code
  needed here. See `notebooks/04_audiveris_grades.ipynb`.
- **homr** computes logits in two networks and keeps only the argmax.
  `homr_confidence.py` runs homr's pipeline in-process with temporary hooks on
  both model calls, and saves:
  - per-pixel class probabilities from the segmentation network
  - per-token probability vectors for all six decoder heads (rhythm, pitch,
    lift, position, articulation, slur), plus each token's attention point
    mapped back to original-page pixels

```bash
python -m omr.homr_confidence example_sheet_music/springar.png -o omr_output/homr
# -> omr_output/homr/springar.confidence.json + springar.confidence.npz
```

```python
from omr.homr_confidence import load_homr_confidence

conf = load_homr_confidence("omr_output/homr/springar.confidence.json")
conf.seg_probs             # (6, h, w) in homr's 1920 px wide page space
conf.tokens[0]["heads"]    # p / margin / entropy / top-3 per head
conf.head_probs["rhythm"]  # (n_tokens, 259) full distributions
```

It produces no MusicXML (use the `homr` engine for that), and it uses private
homr helpers, so it is pinned in practice to homr 0.7.0.
See `notebooks/05_homr_confidence.ipynb`.

## Design notes

- `OMREngine` (in `base.py`) is a small ABC — `is_available()` for a clear
  pre-flight error message instead of a cryptic subprocess/import failure,
  and `run(input_path, output_dir) -> OMRResult`.
- `OMRResult` (also in `base.py`) is a plain dataclass: engine name, output
  format, success flag, output path, and the extracted text when cheap to
  get (MusicXML is unzipped from `.mxl`).
- Adding another engine means adding one file under `engines/` and one line
  in `registry.py` — nothing else in this module needs to change.
