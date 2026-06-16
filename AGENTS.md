# AGENTS

## Project Idea

This project explores music recognition as sensor fusion between a notated page
and a performed audio signal.

The theoretical basis is `type-lowering.pdf`: data is lowered into positional
indicator fields or bitmaps instead of treating sequence traversal as the main
control structure. The goal is to use positional indexes, overlap, coverage,
neighborhoods, and annotation relations to let uncertain sources of evidence
constrain each other.

For this project, OMR and audio should not be assumed to share one perfect
index space. Treat them as distinct but alignable universes:

```text
U_image   pixel and staff geometry
U_score   symbolic or quasi-symbolic score positions
U_audio   frames, onsets, and spectral evidence
U_anchor  musically meaningful landmarks
```

The current working idea is that one modality can annotate the other. A visual
staff line, notehead, audio onset, chroma region, or barline may over-cover,
under-cover, intersect, or support another positional field without being equal
to it.

## Current State

- Read `manifest.md` first.
- `idea-manifest.md` is an older raw sketch.
- `type-lowering.pdf` is the mathematical background.
- `notebooks/01_omr_probe.ipynb` is the first practical notebook.
- `page-000.png` is the current page image used by the notebook.
- `pyproject.toml` uses Python `>=3.12,<3.14` and includes `jupyter` and
  `opencv-python`.

The first notebook has shown promising horizontal/staff-line evidence. The
latest observed result was that the horizontal evidence and morphological
horizontal filtering looked good visually.

## Working Style

Move slowly and keep the human in the loop. Prefer small notebooks and visual
inspection over large automatic pipelines.

Do not jump directly to full note recognition or audio alignment. The likely
next step is:

```text
horizontal evidence -> row bands -> groups of five -> staff systems
```

After staff systems are stable, the project can explore how noteheads, pitch
positions, audio onsets, Fourier/chroma evidence, and annotation relations fit
into the same positional-index framework.
