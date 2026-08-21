"""A/B comparison of the v1 (linear-domain) and v2 (density-domain) engines.

Processes one image with both engines using the same preset/mask and reports a
quick numerical comparison, saving both outputs side by side.

Usage:
    python scripts/compare_v1_v2.py <image> [-c config] [-p preset]
                                          [-o output_dir] [--area x1,y1,x2,y2]

Example:
    python scripts/compare_v1_v2.py D:/neg/scan.tiff -c config.yaml \\
        -p kodak_ultramax_400 -o D:/tmp/ab --area 500,300,4000,2800

The --area ROI doubles as the sampling window (white point for v1, density
endpoints for v2). When it points at a roughly neutral gray patch, the
"neutral spread" row is a direct colour-accuracy proxy: smaller = more neutral.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# Make `python scripts/compare_v1_v2.py` work from anywhere in the repo.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cli.lib.process_film import process_film_bytestream_with_params  # noqa: E402
from cli.openlucky import get_preset_config, parse_area  # noqa: E402


def _decode(bytes_out):
    arr = cv2.imdecode(np.frombuffer(bytes_out, np.uint8), cv2.IMREAD_UNCHANGED)
    rgb = arr[..., ::-1] if arr.ndim == 3 else arr
    return rgb.astype(np.float32) / (65535.0 if arr.dtype == np.uint16 else 255.0)


def _stats(img, name):
    means = img.reshape(-1, 3).mean(axis=0)
    stds = img.reshape(-1, 3).std(axis=0)
    spread = float(img.max(axis=2).mean() - img.min(axis=2).mean())
    return (f"{name:>6s}  mean R/G/B = [{means[0]:.3f} {means[1]:.3f} {means[2]:.3f}]"
            f"  std = [{stds[0]:.3f} {stds[1]:.3f} {stds[2]:.3f}]"
            f"  luma-spread = {spread:.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=Path, help="Input film negative")
    ap.add_argument("-c", "--config", type=Path, default=None)
    ap.add_argument("-p", "--preset", default="kodak_ultramax_400")
    ap.add_argument("-o", "--output-dir", type=Path, default=Path("ab_out"))
    ap.add_argument("--area", default=None,
                    help='Sampling area "x1,y1,x2,y2" (same frame as the pipeline)')
    args = ap.parse_args()

    if not args.image.exists():
        sys.exit(f"Input not found: {args.image}")

    config = args.config if args.config else REPO_ROOT / "config.yaml"
    if not config.exists():
        sys.exit(f"Config not found: {config}")

    preset = get_preset_config(config, args.preset)
    roi = parse_area(args.area) if args.area else None
    input_bytes = args.image.read_bytes()
    is_raw = args.image.suffix.lower() in {".arw", ".cr2", ".cr3", ".nef", ".dng",
                                           ".orf", ".raf", ".fff"}

    common = dict(
        preset_mask_r=preset["mask_r"], preset_mask_g=preset["mask_g"],
        preset_mask_b=preset["mask_b"],
        preset_contrast_r=preset.get("contrast_r", 1.0),
        preset_contrast_g=preset.get("contrast_g", 1.0),
        preset_contrast_b=preset.get("contrast_b", 1.0),
        preset_gamma=preset.get("gamma", 1.0),
        preset_contrast=preset.get("contrast", 1.0),
        white_balance="auto",
        tone_pivot=0.5, tone_curve=0.5,
        is_raw=is_raw,
        wp_roi_x1=roi[0] if roi else None, wp_roi_y1=roi[1] if roi else None,
        wp_roi_x2=roi[2] if roi else None, wp_roi_y2=roi[3] if roi else None,
        saturation=preset.get("saturation", 1.0),
    )

    v1 = process_film_bytestream_with_params(input_bytes, algo="v1", **common)
    v2 = process_film_bytestream_with_params(input_bytes, algo="v2", **common)
    if v1 is None or v2 is None:
        sys.exit("One engine failed to process the image")

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "v1.tif").write_bytes(v1)
    (out_dir / "v2.tif").write_bytes(v2)

    print(f"image: {args.image.name}  preset: {args.preset}  roi: {roi or 'full'}")
    print(f"  v1 -> {out_dir / 'v1.tif'}  ({len(v1)} bytes)")
    print(f"  v2 -> {out_dir / 'v2.tif'}  ({len(v2)} bytes)")
    print("  " + _stats(_decode(v1), "v1"))
    print("  " + _stats(_decode(v2), "v2"))

    if roi:
        def _roi_means(img):
            x1, y1, x2, y2 = roi
            patch = img[y1:y2, x1:x2].reshape(-1, 3)
            return patch.mean(axis=0)
        m1 = _roi_means(_decode(v1))
        m2 = _roi_means(_decode(v2))
        print(f"  ROI mean v1 = [{m1[0]:.3f} {m1[1]:.3f} {m1[2]:.3f}]"
              f"  spread {float(m1.max() - m1.min()):.3f}")
        print(f"  ROI mean v2 = [{m2[0]:.3f} {m2[1]:.3f} {m2[2]:.3f}]"
              f"  spread {float(m2.max() - m2.min()):.3f}"
              "   <- smaller spread on a gray patch = more neutral (better)")


if __name__ == "__main__":
    main()
