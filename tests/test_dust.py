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
HIGHLIGHT = (300, 250)
STAR = (130, 220)


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


def test_coloured_highlight_survives():
    img = _make()
    for lvl in (0.0, 0.6):
        out = remove_defects(img, FULL, {"grain_level": lvl, "dust_size": 9})
        diff = np.abs(out[HIGHLIGHT] - img[HIGHLIGHT]).max()
        assert diff < 0.03, f"highlight touched at slider {lvl}: diff={diff:.3f}"


def test_star_survives():
    img = _make()
    out = remove_defects(img, FULL, {"grain_level": 0.6, "dust_size": 9})
    assert np.abs(out[STAR] - img[STAR]).max() < 0.03
    # Aggressive fine end may dim it a little, but never erase it.
    outf = remove_defects(img, FULL, {"grain_level": 0.0, "dust_size": 9})
    assert outf[STAR].max() > 0.5


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


def test_slider_params_maps_grain_level_per_design_spec():
    """pr/024.dust.md §5: dust_gain = 2.5 + 2.0×g (g=0 → 2.5, g=1 → 4.5);
    α = 1 at fine, falls to 0 from g≥0.5 (粗档不平滑颗粒)."""
    from cli.lib.dust import _slider_params

    # 细端 / 中点 / 粗端
    assert _slider_params(0.0) == (1.0, 2.5)
    assert _slider_params(0.5) == (0.0, 3.5)
    assert _slider_params(1.0) == (0.0, 4.5)

    # 细→粗：dust_gain 单调增；α 在 [0, 0.5) 单调降到 0，之后恒为 0
    gains = [_slider_params(g)[1] for g in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert gains == sorted(gains)
    assert all(_slider_params(g)[0] == 0.0 for g in (0.5, 0.75, 1.0))

    # 输入钳位到 [0, 1]
    assert _slider_params(-1.0) == (1.0, 2.5)
    assert _slider_params(2.0) == (0.0, 4.5)


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
