"""Generate synthetic positive images for dust-removal prototype validation.

Deterministic (fixed RNG seed). Each image is a gradient "sky" with synthetic
film grain (luminance + small chroma), plus:

  * several neutral bright dust dots   — must be repaired;
  * one coloured highlight (pinkish)   — must survive (a/b neutrality test);
  * one sub-pixel "star"               — must survive (area filter).

Smoke preview (before / after / mask per 粗细 slider level) writes into
tests/output/dust_smoke/:

    python -m tests.tools.make_dust_samples
"""
from pathlib import Path

import cv2
import numpy as np

from cli.lib.dust import detect_dust_mask, remove_defects

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _add_dot(img, cx, cy, r, color, sigma=None):
    """A gaussian bump above the background (opaque dust ≈ bright disc)."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    if sigma is None:
        sigma = max(0.6, r * 0.6)   # opaque dust ≈ gaussian bump above bg
    g = np.exp(-d2 / (2.0 * sigma * sigma))
    for c in range(3):
        img[:, :, c] = np.maximum(img[:, :, c], g * color[c])


def make_synthetic_positive(seed=0, h=400, w=600, grain_amp=0.06, with_features=True):
    # grain_amp is in [0,1] RGB units: ~0.02-0.03 fine film, ~0.06 coarse
    # (ISO 1600+), 0.10 extreme pushed film (near the discrimination limit).
    """Positive-like float32 RGB in [0,1]."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.stack([
        0.45 + 0.30 * yy / h,
        0.55 + 0.25 * yy / h,
        0.65 + 0.20 * yy / h,
    ], axis=2)
    lum = rng.normal(0, grain_amp, (h, w, 1))
    chroma = rng.normal(0, grain_amp * 0.25, (h, w, 3))
    img = base + 0.85 * lum + chroma
    img = np.clip(img, 0.0, 1.0).astype(np.float32)  # float32 like the pipeline

    if with_features:
        for cx, cy, r in [
            (80, 60, 2.0), (150, 90, 3.0), (240, 70, 4.0),
            (360, 120, 2.5), (470, 80, 3.5), (540, 130, 5.0),
        ]:
            _add_dot(img, cx, cy, r, (1.0, 1.0, 1.0))
        _add_dot(img, 300, 250, 3.0, (1.0, 0.55, 0.55))        # coloured highlight
        _add_dot(img, 130, 220, 0.8, (1.0, 1.0, 1.0), sigma=0.5)  # tiny star
    return img


def _to_bgr_u8(img):
    return (np.clip(img, 0.0, 1.0) * 255.0).astype(np.uint8)[..., ::-1]


def main():
    outdir = REPO_ROOT / "tests" / "output" / "dust_smoke"
    outdir.mkdir(parents=True, exist_ok=True)
    regions = [{"shape": "rect", "x1": 10, "y1": 10, "x2": 590, "y2": 390}]

    for grain_amp, label in [
        (0.03, "fine_grain"),
        (0.06, "coarse_grain"),
        (0.10, "extreme_grain"),   # 近判别极限，验证粗细滑块兜底
    ]:
        img = make_synthetic_positive(seed=0, grain_amp=grain_amp)
        cv2.imwrite(str(outdir / f"{label}_before.png"), _to_bgr_u8(img))

        for level, lvl in [(0.0, "fine"), (0.3, "mid"), (0.6, "coarse")]:
            out = remove_defects(img, regions, {"grain_level": level, "dust_size": 9})
            mask = detect_dust_mask(img, regions[0], {"grain_level": level, "dust_size": 9})
            cv2.imwrite(
                str(outdir / f"{label}_slider_{lvl}_after.png"), _to_bgr_u8(out)
            )
            if mask is not None:
                cv2.imwrite(
                    str(outdir / f"{label}_slider_{lvl}_mask.png"),
                    np.repeat(mask[:, :, None], 3, axis=2),
                )
    print(f"wrote smoke previews to {outdir}")


if __name__ == "__main__":
    main()
