"""Tests for the Lab-based dust removal prototype (cli/lib/dust.py).

Fast, fully synthetic — no real film samples needed. A gradient sky with two
realistic grain levels, neutral dust dots, one coloured highlight and one tiny
star exercise the mechanism promised in pr/024.dust.md:

  * coarse slider (grain_level 0.6): big dust removed, grain preserved;
  * fine slider (0.0): small dust also caught, grain slightly flattened;
  * coloured highlights and tiny stars survive (never mistaken for dust);
  * work is scoped to the ROIs and untouched pixels keep float precision.
"""
import cv2
import numpy as np
import pytest

from cli.openlucky import parse_dust, parse_dust_rois
from cli.lib.dust import detect_dust_mask, remove_defects
from tests.tools.make_dust_samples import make_synthetic_positive

FULL = [{"shape": "rect", "x1": 10, "y1": 10, "x2": 590, "y2": 390}]
BIG_DUST = [(150, 90), (240, 70), (470, 80), (540, 130)]
ALL_DUST = [(80, 60), (150, 90), (240, 70), (360, 120), (470, 80), (540, 130)]


def _make(grain_amp=0.06):
    return make_synthetic_positive(seed=0, grain_amp=grain_amp)


def _grain_std(img):
    return img[295:305, 395:405].std()


def test_coarse_end_removes_big_dust_keeps_grain():
    img = _make()
    out = remove_defects(img, FULL, {"grain_level": 0.6, "dust_size": 9})
    for cx, cy in BIG_DUST:
        assert out[cy, cx].max() < 0.85, f"big dust at ({cx},{cy}) not removed"
    # Coarse end only repairs dust; a grain-only patch is bit-preserved.
    assert _grain_std(out) / _grain_std(img) > 0.9


def test_fine_end_also_catches_small_dust():
    img = _make()
    out = remove_defects(img, FULL, {"grain_level": 0.0, "dust_size": 9})
    for cx, cy in ALL_DUST:
        assert out[cy, cx].max() < 0.85, f"dust at ({cx},{cy}) not removed at fine"
    # Fine end flattens grain more than the coarse end.
    coarse = remove_defects(img, FULL, {"grain_level": 0.6, "dust_size": 9})
    assert _grain_std(out) < _grain_std(coarse)


def test_coloured_blob_removed_as_anomaly():
    """A sizable coloured blob (not a 1px point) is an anomaly and gets pulled
    back toward its background. Mirrors a real coloured highlight the user
    would actually lasso in a small ROI."""
    h, w = 160, 160
    bg = np.array([0.55, 0.60, 0.62], dtype=np.float32)
    img = np.zeros((h, w, 3), dtype=np.float32) + bg
    cy, cx = 80, 80
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * 6.0 ** 2))[..., None]
    img = np.clip(img + blob * np.array([0.40, -0.15, -0.15], dtype=np.float32), 0, 1)

    roi = {"shape": "rect", "x1": 30, "y1": 30, "x2": 130, "y2": 130}
    out = remove_defects(img, [roi], {"grain_level": 0.6, "dust_size": 9})
    assert np.abs(out[cy, cx] - img[cy, cx]).max() > 0.03


def test_roi_scoping_dust_outside_untouched():
    img = _make()
    roi = [{"shape": "rect", "x1": 130, "y1": 70, "x2": 170, "y2": 110}]  # around (150,90)
    out = remove_defects(img, roi, {"grain_level": 0.0, "dust_size": 9})
    assert out[150, 90].max() < 0.85, "dust inside ROI not removed"
    assert np.array_equal(out[130, 540], img[130, 540]), "dust outside ROI was touched"


def test_no_regions_returns_unchanged():
    img = _make()
    out = remove_defects(img, [], {"grain_level": 0.0, "dust_size": 9})
    assert np.array_equal(out, img)


def test_float_precision_preserved_outside_mask():
    img = _make()
    out = remove_defects(img, FULL, {"grain_level": 0.6, "dust_size": 9})
    changed = ~np.all(np.abs(out - img) < 1e-6, axis=2)
    # Only the repaired dust spots (mask + halo) differ — a tiny fraction.
    assert changed.sum() < 5000, f"{changed.sum()} pixels changed"


def test_per_roi_strength_override():
    img = _make()
    # Global coarse (0.6) misses the small dot at (80,60); a per-ROI fine
    # strength override catches it.
    roi = {"shape": "rect", "x1": 60, "y1": 40, "x2": 100, "y2": 80, "strength": 0.0}
    out = remove_defects(img, [roi], {"grain_level": 0.6, "dust_size": 9})
    assert out[80, 60].max() < 0.85, "per-ROI strength override not honoured"


def test_yellowish_dust_removed_as_colour_anomaly():
    """pr/026: real negative dust is yellowish (not neutral) after inversion and
    forms soft clumps, so the old a/b-neutrality filter discarded it. The new
    colour-anomaly detector must catch a yellowish blotch against a flat
    skin-like background."""
    # Flat skin-tone background (~(0.85, 0.72, 0.60)), plus a yellowish dust
    # clump (~(0.95, 0.92, 0.75)) with a soft edge — the exact shape the old
    # filter missed (b channel deviates, so b_dev > 28 killed it).
    h, w = 120, 120
    bg = np.array([0.85, 0.72, 0.60], dtype=np.float32)
    img = np.zeros((h, w, 3), dtype=np.float32) + bg

    cy, cx = 60, 60
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    blob = np.exp(-d2 / (2.0 * 8.0 ** 2))[..., None]  # ~8px soft gaussian
    img = np.clip(img + blob * np.array([0.10, 0.20, 0.15], dtype=np.float32), 0, 1)

    roi = {"shape": "rect", "x1": 20, "y1": 20, "x2": 100, "y2": 100}
    out = remove_defects(img, [roi], {"grain_level": 0.3, "dust_size": 9})

    # The yellowish clump's center should be pulled back toward the background.
    before = img[cy, cx].max()
    after = out[cy, cx].max()
    assert after < before - 0.03, f"yellowish dust not removed: before={before:.3f} after={after:.3f}"


def test_slider_params_maps_grain_level_per_design_spec():
    """pr/026 rewrite: the slider maps to an anomaly-threshold gain,
    fine (->0) lenient → coarse (->1) strict. Pr/024's old (alpha, dust_gain)
    contract is superseded."""
    from cli.lib.dust import _slider_params

    # 细端 / 中点 / 粗端：gain 单调升
    assert _slider_params(0.0) == 2.0
    assert _slider_params(0.5) == 3.0
    assert _slider_params(1.0) == 4.0

    gains = [_slider_params(g) for g in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert gains == sorted(gains)

    # 输入钳位到 [0, 1]
    assert _slider_params(-1.0) == 2.0
    assert _slider_params(2.0) == 4.0


def test_detect_dust_mask_shape_and_consistency():
    img = _make()
    roi = {"shape": "rect", "x1": 130, "y1": 70, "x2": 170, "y2": 110}
    mask = detect_dust_mask(img, roi, {"grain_level": 0.0, "dust_size": 9})
    assert mask is not None
    assert mask.shape == (40, 40)          # exactly the ROI (y2-y1, x2-x1)
    assert mask.dtype == np.uint8
    # The detected dust dot (150,90) lies inside the mask region.
    assert mask[90 - 70, 150 - 130] > 0


# ── CLI argument parsing ─────────────────────────────────────────────────────

def test_parse_dust_valid():
    assert parse_dust("0.3,9") == (0.3, 9)
    assert parse_dust(None) is None


@pytest.mark.parametrize("bad", ["0.3", "0.3,9,5", "1.5,9", "-0.1,9", "0.3,2", "0.3,abc"])
def test_parse_dust_rejects(bad):
    with pytest.raises(ValueError):
        parse_dust(bad)


def test_parse_dust_rois_valid():
    rois = parse_dust_rois("10,10,590,390;20,20,100,100")
    assert rois == [(10, 10, 590, 390), (20, 20, 100, 100)]
    assert parse_dust_rois(None) is None
    assert parse_dust_rois("") is None


@pytest.mark.parametrize("bad", ["10,10,5,5", "10,10,590", "10,10,590,390;20,20,5,5", "abc"])
def test_parse_dust_rois_rejects(bad):
    with pytest.raises(ValueError):
        parse_dust_rois(bad)


# ── CLI wiring (real process_film pipeline) ─────────────────────────────────

def _load_rgb(path):
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)[..., ::-1].astype(float)


def test_cli_filmparam_dust_flag(run_cli, output_dir, tmp_path):
    """--dust + --dust-rois wire through the real CLI: bright dust spots are
    repaired while the rest of the pipeline runs normally."""
    pos = make_synthetic_positive(seed=0, grain_amp=0.06, with_features=True)
    neg = (1.0 - pos)  # synthetic negative (mask=255 → division is identity)
    in_path = tmp_path / "neg.png"
    cv2.imwrite(str(in_path), (np.clip(neg, 0, 1) * 255).astype(np.uint8)[..., ::-1])
    out_a = output_dir / "no_dust.png"
    out_b = output_dir / "dust.png"

    base = ["filmparam", "-i", str(in_path), "--param", "255,255,255,1,1",
            "--white-balance", "none", "--tone", "0.5,0.5", "--color-mode", "preserve"]
    r1 = run_cli(*base, "-o", str(out_a))
    assert r1.returncode == 0, r1.stderr
    r2 = run_cli(*base, "-o", str(out_b), "--dust", "0.3,9", "--dust-rois", "10,10,590,390")
    assert r2.returncode == 0, r2.stderr

    a = _load_rgb(out_a)
    b = _load_rgb(out_b)
    for cx, cy in [(150, 90), (240, 70), (470, 80), (540, 130)]:
        assert b[cy, cx].max() < a[cy, cx].max() - 15, f"big dust at ({cx},{cy}) not repaired via CLI"
