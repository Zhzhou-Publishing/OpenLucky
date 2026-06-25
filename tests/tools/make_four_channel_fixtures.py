"""Generate the committed 4-channel (RGB+IR) TIFF fixtures.

Real film scanners (e.g. the Flextight/Imacon path) emit 16-bit RGB scans with a
4th *infrared* sample used for dust/scratch removal, and frequently omit the
`ExtraSamples` tag — which makes libtiff warn and Chromium/sharp mis-read the IR
band as alpha. The OpenLucky pipeline only needs RGB, so it drops the 4th band on
read. These fixtures reproduce that 4-sample structure (small, so they can be
committed) and feed the otherwise-skipped `@pytest.mark.slow` integration tests:

  tests/input_sample_none_raw/sample_rgbi_16bit.tiff  -> resize / reshape /
      filmparam / filmparambatch / filmbatch / tiff2jpeg
  tests/input_sample_strip/strip_rgbi_16bit.tiff      -> tool split (real strip)

Regenerate with:  python -m tests.tools.make_four_channel_fixtures
The output is deterministic (fixed RNG seed), so re-running is a no-op in git.
"""
from pathlib import Path

import numpy as np
import tifffile

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
NONE_RAW_DIR = REPO_ROOT / "tests" / "input_sample_none_raw"
STRIP_DIR = REPO_ROOT / "tests" / "input_sample_strip"


def _add_ir(rgb_u16, seed):
    """Append a 4th (infrared-like) 16-bit band to an (H, W, 3) uint16 array.

    The IR band is deliberately uncorrelated with and brighter than RGB, like a
    real IR cleaning channel — so any code that wrongly treats it as colour or
    alpha produces visibly wrong output the tests can catch.
    """
    rng = np.random.default_rng(seed)
    h, w = rgb_u16.shape[:2]
    ir = np.clip(rng.normal(0.85, 0.05, (h, w)), 0, 1)
    ir = (ir * 65535).astype(np.uint16)
    return np.concatenate([rgb_u16, ir[:, :, None]], axis=2)


def make_photo(path, w=200, h=150, seed=7):
    """A small RGB+IR scan: smooth per-channel gradients + light grain."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = xx / (w - 1)
    g = yy / (h - 1)
    b = (1.0 - r + g) / 2.0
    rgb = np.stack([r, g, b], axis=2)
    rgb = np.clip(rgb + rng.normal(0, 0.02, rgb.shape), 0, 1)
    rgb_u16 = (rgb * 65535).astype(np.uint16)
    arr = _add_ir(rgb_u16, seed + 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    # photometric='rgb' with 4 samples mirrors the real scan; deflate keeps the
    # committed fixture small while staying lossless.
    tifffile.imwrite(str(path), arr, photometric="rgb", compression="deflate")
    print(f"wrote {path}  shape={arr.shape} dtype={arr.dtype}")


def make_strip(path, frames=3, fh=180, gap=30, band_w=140, sprocket_w=15,
               baffle_w=15, topb=40, botb=40, seed=0):
    """A vertical film-strip scan (RGB+IR) with `frames` detectable frames.

    Mirrors the layout `tests/test_tool_split.py::_make_synthetic_strip` builds,
    plus a 4th IR band, so `tool split` exercises the drop-IR path end to end.
    """
    rng = np.random.default_rng(seed)
    W = 2 * baffle_w + 2 * sprocket_w + band_w
    sl0, sl1 = baffle_w, baffle_w + sprocket_w
    b0, b1 = sl1, sl1 + band_w
    sr0, sr1 = b1, b1 + sprocket_w

    def base_row(fill_band):
        row = np.full(W, 0.10)
        row[sl0:sl1] = 0.90
        row[sr0:sr1] = 0.90
        row[b0:b1] = fill_band
        return row

    rows = [base_row(0.10) for _ in range(topb)]
    for f in range(frames):
        for _ in range(fh):
            r = base_row(0.45)
            r[b0:b1] = np.clip(rng.normal(0.45, 0.12, b1 - b0), 0, 1)
            rows.append(r)
        if f < frames - 1:
            rows += [base_row(0.85) for _ in range(gap)]
    rows += [base_row(0.10) for _ in range(botb)]

    u16 = (np.array(rows) * 65535).astype(np.uint16)
    rgb_u16 = np.stack([u16] * 3, axis=2)
    arr = _add_ir(rgb_u16, seed + 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(path), arr, photometric="rgb", compression="deflate")
    print(f"wrote {path}  shape={arr.shape} dtype={arr.dtype}")


def main():
    make_photo(NONE_RAW_DIR / "sample_rgbi_16bit.tiff")
    make_strip(STRIP_DIR / "strip_rgbi_16bit.tiff")


if __name__ == "__main__":
    main()
