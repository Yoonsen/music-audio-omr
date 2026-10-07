"""Run homr and keep the model scores it normally throws away.

homr takes an argmax at every model output and keeps only the winning class.
This module runs homr's own pipeline unchanged, but temporarily hooks the two
places where a network is called, so the full score vectors are kept:

- segmentation (Segnet): six class logits per pixel -> per-pixel probabilities
  for background / stem_rest / notehead / clef_key / staff / symbol
- staff transformer (TrOMR decoder): six logit vectors per output token
  (rhythm, pitch, lift, position, articulation, slur) -> per-token confidence,
  plus the attention point the decoder reports for that token

Nothing in the installed homr package is edited, and the hooks are removed
again when `run_homr_with_confidence` returns. Written against homr 0.7.0;
several private homr helpers are used, so other versions may need adjusting.

Coordinate spaces:

    original   the input image as given
    homr       homr's working page: autocropped, then resized to 1920 px wide.
               Segmentation probabilities and staff regions live here.
    canvas     one staff, cropped, dewarped and placed on a 1280 x 256 canvas.
               This is what the transformer sees; attention points live here.

`HomrConfidence.homr_to_original` maps homr -> original exactly. Tokens also
carry an approximate position in original-page coordinates: the mapping from
canvas back to homr ignores homr's per-staff dewarping, which moves things by
at most a few pixels on a straight scan.
"""
from __future__ import annotations

import json
from concurrent.futures import Future
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

SEGNET_CLASSES = ["background", "stem_rest", "notehead", "clef_key", "staff", "symbol"]
DECODER_HEADS = ["rhythm", "pitch", "lift", "position", "articulation", "slur"]
TOP_K = 3


def _softmax(logits: np.ndarray, axis: int) -> np.ndarray:
    z = logits - logits.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


@dataclass
class HomrConfidence:
    image_path: Path
    original_shape: tuple[int, int]  # (h, w)
    homr_shape: tuple[int, int]  # (h, w)
    crop_offset: tuple[int, int]  # (x, y) of homr's autocrop in the original image
    scale: tuple[float, float]  # (sx, sy): homr pixels per original pixel
    class_names: list[str]
    seg_probs: np.ndarray  # (classes, h, w) float32 in homr space
    staffs: list[dict]
    tokens: list[dict]  # tokens[i]["index"] == i, the row in head_probs
    vocabs: dict[str, list[str]]  # decoder head -> token names by class index
    head_probs: dict[str, np.ndarray]  # decoder head -> (n_tokens, vocab size) probabilities
    canvases: list[np.ndarray] = field(default_factory=list)  # transformer input per staff

    def homr_to_original(self, x, y):
        x = np.asarray(x, dtype=float) / self.scale[0] + self.crop_offset[0]
        y = np.asarray(y, dtype=float) / self.scale[1] + self.crop_offset[1]
        return x, y

    def seg_probs_original(self) -> np.ndarray:
        """Segmentation probabilities resampled onto the original image (zero outside the crop)."""
        h, w = self.original_shape
        ox, oy = self.crop_offset
        crop_w = round(self.homr_shape[1] / self.scale[0])
        crop_h = round(self.homr_shape[0] / self.scale[1])
        out = np.zeros((len(self.class_names), h, w), dtype=np.float32)
        for c, plane in enumerate(self.seg_probs):
            out[c, oy : oy + crop_h, ox : ox + crop_w] = cv2.resize(
                plane, (crop_w, crop_h), interpolation=cv2.INTER_LINEAR
            )
        return out

    def save(self, output_dir: Path) -> tuple[Path, Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = self.image_path.stem
        json_path = output_dir / f"{stem}.confidence.json"
        npz_path = output_dir / f"{stem}.confidence.npz"
        meta = dict(
            image_path=str(self.image_path),
            original_shape=list(self.original_shape),
            homr_shape=list(self.homr_shape),
            crop_offset=list(self.crop_offset),
            scale=list(self.scale),
            class_names=self.class_names,
            staffs=self.staffs,
            tokens=self.tokens,
            vocabs=self.vocabs,
        )
        json_path.write_text(json.dumps(meta, indent=1))
        # Segmentation probabilities quantized to 1/255 steps: plenty for inspection, ~4x smaller.
        np.savez_compressed(
            npz_path,
            seg_probs=np.round(self.seg_probs * 255).astype(np.uint8),
            **{f"probs_{head}": p.astype(np.float16) for head, p in self.head_probs.items()},
            **{f"canvas_{i}": c for i, c in enumerate(self.canvases)},
        )
        return json_path, npz_path


def load_homr_confidence(json_path: Path) -> HomrConfidence:
    json_path = Path(json_path)
    meta = json.loads(json_path.read_text())
    data = np.load(json_path.with_name(json_path.name.replace(".json", ".npz")))
    return HomrConfidence(
        image_path=Path(meta["image_path"]),
        original_shape=tuple(meta["original_shape"]),
        homr_shape=tuple(meta["homr_shape"]),
        crop_offset=tuple(meta["crop_offset"]),
        scale=tuple(meta["scale"]),
        class_names=meta["class_names"],
        seg_probs=data["seg_probs"].astype(np.float32) / 255,
        staffs=meta["staffs"],
        tokens=meta["tokens"],
        vocabs=meta["vocabs"],
        head_probs={head: data[f"probs_{head}"].astype(np.float32) for head in meta["vocabs"]},
        canvases=[data[f"canvas_{i}"] for i in range(len(meta["staffs"]))],
    )


# --- hooks -------------------------------------------------------------------


@contextmanager
def _capture_segnet():
    """Record homr's Segnet tiles (as probabilities) and the tiling geometry."""
    from homr.segmentation import inference_segnet

    captured: dict = {"tiles": []}
    original_run = inference_segnet.Segnet.run
    original_inference = inference_segnet.inference

    def run(self, input_data):
        out = original_run(self, input_data)
        captured["tiles"].extend(_softmax(out.astype(np.float32), axis=1).astype(np.float16))
        return out

    def inference(image_org, use_gpu_inference, batch_size, step_size, win_size):
        captured["shape"] = image_org.shape[:2]
        captured["step"] = step_size if step_size >= 0 else win_size // 2
        captured["win"] = win_size
        return original_inference(image_org, use_gpu_inference, batch_size, step_size, win_size)

    inference_segnet.Segnet.run = run
    inference_segnet.inference = inference
    try:
        yield captured
    finally:
        inference_segnet.Segnet.run = original_run
        inference_segnet.inference = original_inference


def _merge_tiles(tiles: list[np.ndarray], shape: tuple[int, int], step: int, win: int) -> np.ndarray:
    # Same tile order and placement as homr's inference()/merge_patches(), but averaging
    # probabilities where tiles overlap instead of averaging argmax class indices.
    h, w = shape
    probs = np.zeros((tiles[0].shape[0], h, w), dtype=np.float32)
    weight = np.zeros((h, w), dtype=np.float32)
    idx = 0
    for y_loop in range(0, max(h, win), step):
        y = max(min(y_loop, h - win), 0)
        for x_loop in range(0, max(w, win), step):
            x = max(min(x_loop, w - win), 0)
            ph, pw = min(win, h - y), min(win, w - x)
            probs[:, y : y + ph, x : x + pw] += tiles[idx][:, :ph, :pw]
            weight[y : y + ph, x : x + pw] += 1
            idx += 1
    if idx != len(tiles):
        raise RuntimeError(f"expected {idx} segnet tiles, captured {len(tiles)}")
    return probs / np.maximum(weight, 1)


@contextmanager
def _capture_decoder(decoder):
    """Record each decoder step's six logit vectors and its attention point."""
    steps: list[dict] = []
    net = decoder.net
    original = net.run_with_iobinding

    def run_with_iobinding(iobinding, run_options=None):
        original(iobinding, run_options)
        outputs = iobinding.get_outputs()
        steps.append(
            dict(
                logits=[outputs[k].numpy()[0, -1].astype(np.float32) for k in range(len(DECODER_HEADS))],
                attention=outputs[len(DECODER_HEADS)].numpy().astype(float).tolist(),
            )
        )

    net.run_with_iobinding = run_with_iobinding
    try:
        yield steps
    finally:
        del net.run_with_iobinding  # drop the instance attribute, back to the class method


# --- coordinates -------------------------------------------------------------


def _autocrop_offset(image: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
    from homr.autocrop import autocrop

    cropped = autocrop(image)
    if cropped is image:
        return cropped, (0, 0)
    # autocrop returns a slice (a view) of the input, so its offset follows from the
    # distance between the two data pointers.
    delta = cropped.__array_interface__["data"][0] - image.__array_interface__["data"][0]
    y, rest = divmod(delta, image.strides[0])
    return cropped, (rest // image.strides[1], y)


def _canvas_to_homr(staff, regions, homr_shape: tuple[int, int]):
    """Invert prepare_staff_image()'s scale/crop/centre steps (not its dewarp)."""
    from homr.image_utils import crop_image_and_return_new_top
    from homr.staff_parsing import _calculate_region, get_tr_omr_canvas_size, tr_omr_max_height

    region = _calculate_region(staff, regions)
    canvas_w, canvas_h = get_tr_omr_canvas_size((int(region[3] - region[1]), int(region[2] - region[0])))
    s = canvas_h / (region[3] - region[1])
    scaled = np.broadcast_to(np.uint8(0), (int(homr_shape[0] * s), int(homr_shape[1] * s)))
    region_s = np.round(region * s)
    crop1, top_left1 = crop_image_and_return_new_top(scaled, *(region_s + np.array([-10, -50, 10, 50])))
    crop2, top_left2 = crop_image_and_return_new_top(crop1, *(region_s - np.array([*top_left1, *top_left1])))
    h2, w2 = crop2.shape[:2]
    y_offset = (tr_omr_max_height - canvas_h) // 2
    origin = top_left1 + top_left2

    def to_homr(u: float, v: float) -> tuple[float, float]:
        x = (u * w2 / canvas_w + origin[0]) / s
        y = ((v - y_offset) * h2 / canvas_h + origin[1]) / s
        return float(x), float(y)

    return to_homr, region


# --- token statistics --------------------------------------------------------


def _head_stats(p: np.ndarray, inv_vocab: dict[int, str]) -> dict:
    order = np.argsort(p)[::-1]
    entropy = float(-(p * np.log(np.clip(p, 1e-12, None))).sum())
    return dict(
        token=inv_vocab[int(order[0])],
        p=float(p[order[0]]),
        margin=float(p[order[0]] - p[order[1]]),
        entropy=entropy,
        entropy_norm=entropy / np.log(len(p)),  # 0 = certain, 1 = uniform over the vocabulary
        top=[[inv_vocab[int(i)], float(p[i])] for i in order[:TOP_K]],
    )


# --- main entry point --------------------------------------------------------


def run_homr_with_confidence(
    image_path: Path, output_dir: Path | None = None, use_gpu: bool = False
) -> HomrConfidence:
    """Run homr's staff detection + transformer on one image and keep all scores.

    Produces no MusicXML (use the regular `homr` engine for that); the tokens here
    are the raw per-staff transformer output before homr merges voices and removes
    duplicates. If `output_dir` is given, results are saved there as
    `<stem>.confidence.json` + `<stem>.confidence.npz`.
    """
    from homr import main as homr_main
    from homr.resize import calc_target_image_size
    from homr.staff_parsing import _ensure_same_number_of_staffs, prepare_staff_image
    from homr.staff_regions import StaffRegions
    from homr.transformer.configs import Config
    from homr.transformer.staff2score import Staff2Score

    image_path = Path(image_path).resolve()
    original = cv2.imread(str(image_path))
    if original is None:
        raise ValueError(f"cannot read image: {image_path}")
    cropped, crop_offset = _autocrop_offset(original)
    homr_w, homr_h = calc_target_image_size(cropped.shape[1], cropped.shape[0])
    scale = (homr_w / cropped.shape[1], homr_h / cropped.shape[0])

    def to_original(x, y):
        return x / scale[0] + crop_offset[0], y / scale[1] + crop_offset[1]

    homr_main.download_weights(use_gpu, use_gpu, False)
    config = homr_main.ProcessingConfig(
        enable_debug=False,
        enable_cache=False,
        write_staff_positions=False,
        read_staff_positions=False,
        selected_staff=-1,
        transformer_use_gpu=use_gpu,
        segnet_use_gpu=use_gpu,
        coreml_encoder=False,
    )

    # Skip homr's title OCR: it is slow and irrelevant here.
    original_detect_title = homr_main.detect_title
    no_title: Future[str] = Future()
    no_title.set_result("")
    homr_main.detect_title = lambda *args, **kwargs: no_title
    try:
        with _capture_segnet() as seg:
            multi_staffs, page, debug, _ = homr_main.detect_staffs_in_image(str(image_path), config)
    finally:
        homr_main.detect_title = original_detect_title

    if page.shape[:2] != (homr_h, homr_w):
        raise RuntimeError(f"homr page is {page.shape[:2]}, expected {(homr_h, homr_w)}")
    seg_probs = _merge_tiles(seg["tiles"], seg["shape"], seg["step"], seg["win"])

    transformer_config = Config()
    transformer_config.use_gpu_inference = use_gpu
    model = Staff2Score(transformer_config)
    inv_vocabs = {
        head: {v: k for k, v in getattr(transformer_config, f"{head}_vocab").items()}
        for head in DECODER_HEADS
    }

    # Same staff order and numbering as homr's parse_staffs().
    systems = _ensure_same_number_of_staffs(multi_staffs, page)
    regions = StaffRegions(systems)
    staffs, tokens, canvases = [], [], []
    head_probs: dict[str, list[np.ndarray]] = {head: [] for head in DECODER_HEADS}
    index = 0
    for voice in range(len(systems[0].staffs)):
        for system_index, system in enumerate(systems):
            staff = system.staffs[voice]
            to_homr, region = _canvas_to_homr(staff, regions, page.shape[:2])
            canvas, _ = prepare_staff_image(debug, index, staff, page, regions=regions)
            with _capture_decoder(model.decoder) as steps:
                symbols = model.predict(canvas)

            rx, ry = to_original(np.array([staff.min_x, staff.max_x]), np.array([staff.min_y, staff.max_y]))
            staffs.append(
                dict(
                    index=index,
                    voice=voice,
                    system=system_index,
                    is_grandstaff=bool(staff.is_grandstaff),
                    unit_size_homr=float(staff.average_unit_size),
                    region_homr=[float(v) for v in region],
                    box_original=[float(rx[0]), float(ry[0]), float(rx[1]), float(ry[1])],
                )
            )
            canvases.append(canvas)

            for step, (symbol, record) in enumerate(zip(symbols, steps)):
                probs = {
                    head: _softmax(logits.astype(np.float64), axis=-1)
                    for head, logits in zip(DECODER_HEADS, record["logits"])
                }
                heads = {head: _head_stats(p, inv_vocabs[head]) for head, p in probs.items()}
                if heads["rhythm"]["token"] != symbol.rhythm:
                    raise RuntimeError(
                        f"staff {index} step {step}: captured {heads['rhythm']['token']!r}, "
                        f"homr produced {symbol.rhythm!r}"
                    )
                u, v = record["attention"]
                if np.isfinite(u) and np.isfinite(v):
                    ox, oy = (float(c) for c in to_original(*to_homr(u, v)))
                else:
                    ox = oy = None
                for head, p in probs.items():
                    head_probs[head].append(p)
                tokens.append(
                    dict(
                        index=len(tokens),
                        staff=index,
                        step=step,
                        # homr drops "lower" tokens on single (non-grand) staves.
                        kept=bool(staff.is_grandstaff or symbol.position != "lower"),
                        canvas_xy=[u, v],
                        original_xy=[ox, oy],
                        heads=heads,
                    )
                )
            index += 1

    result = HomrConfidence(
        image_path=image_path,
        original_shape=original.shape[:2],
        homr_shape=(homr_h, homr_w),
        crop_offset=crop_offset,
        scale=scale,
        class_names=SEGNET_CLASSES,
        seg_probs=seg_probs,
        staffs=staffs,
        tokens=tokens,
        vocabs={head: [inv_vocabs[head][i] for i in range(len(inv_vocabs[head]))] for head in DECODER_HEADS},
        head_probs={head: np.array(rows, dtype=np.float32) for head, rows in head_probs.items()},
        canvases=canvases,
    )
    if output_dir is not None:
        result.save(output_dir)
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m omr.homr_confidence",
        description="Run homr and save per-pixel and per-token confidence.",
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("omr_output/homr"))
    parser.add_argument("--gpu", action="store_true", help="Use CUDA if available")
    args = parser.parse_args(argv)

    result = run_homr_with_confidence(args.image, args.output, use_gpu=args.gpu)
    print(f"{len(result.staffs)} staves, {len(result.tokens)} tokens -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
