"""Command-line entry point: `python -m omr <engine> <input> [options]`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import recognize
from .base import OMRError
from .registry import ENGINES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omr", description="Run one OMR engine on an image or PDF."
    )
    parser.add_argument("engine", choices=sorted(ENGINES), help="OMR engine to run")
    parser.add_argument("input", type=Path, help="Input image or PDF")
    parser.add_argument("-o", "--output", type=Path, default=Path("omr_output"))
    parser.add_argument("--audiveris-bin", help="Path to the Audiveris executable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    engine_kwargs = {}
    if args.engine == "audiveris" and args.audiveris_bin:
        engine_kwargs["binary"] = args.audiveris_bin

    try:
        results = recognize(args.input, engine=args.engine, output_dir=args.output, **engine_kwargs)
    except OMRError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    exit_code = 0
    for result in results:
        status = "OK" if result.success else "FAILED"
        print(f"[{status}] {result.input_path} -> {result.output_path}")
        if not result.success:
            exit_code = 1
            if result.stderr:
                print(result.stderr, file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
