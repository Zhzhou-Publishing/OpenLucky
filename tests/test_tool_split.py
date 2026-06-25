"""Tests for `cli.openlucky tool split` and the detector in cli.lib.tool.split."""
import json

import numpy as np
import pytest
import tifffile

from cli.lib.tool.split import detect_frames


def _make_synthetic_strip(frames=6, fh=270, gap=30, band_w=140, sprocket_w=15,
                          baffle_w=15, sprockets=True, sprocket_val=0.90,
                          channels=3, seed=0, frame_mean=0.45, frame_std=0.12,
                          gap_val=0.85, baffle_val=0.10, topb=40, botb=40):
    """Build a vertical strip scan for testing, parameterised across formats.

    Short axis: dark baffle | [bright sprocket] | image band | [bright sprocket]
    | dark baffle. With sprockets=False there are no perforations (120 medium
    format). Long axis: dark baffle, then `frames` textured frames separated by
    bright+smooth inter-frame gaps (clear film base).

    `fh` sets frame height (vary it for 645/6x6/6x7/6x9 aspect ratios),
    `frames` the count (longer strips), `channels` 1 (B&W grayscale, 2-D array)
    or 3 (color, RGB). Defaults reproduce the original 135 layout (W=200,
    image band [30,170]).
    """
    rng = np.random.default_rng(seed)
    if sprockets:
        W = 2 * baffle_w + 2 * sprocket_w + band_w
        sl0, sl1 = baffle_w, baffle_w + sprocket_w
        b0, b1 = sl1, sl1 + band_w
        sr0, sr1 = b1, b1 + sprocket_w
    else:
        W = 2 * baffle_w + band_w
        b0, b1 = baffle_w, baffle_w + band_w
        sl0 = sl1 = sr0 = sr1 = -1

    def base_row(fill_band):
        row = np.full(W, baffle_val)
        if sprockets:
            row[sl0:sl1] = sprocket_val
            row[sr0:sr1] = sprocket_val
        row[b0:b1] = fill_band
        return row

    rows = []
    rows += [base_row(baffle_val) for _ in range(topb)]
    for f in range(frames):
        for _ in range(fh):
            r = base_row(frame_mean)
            r[b0:b1] = np.clip(rng.normal(frame_mean, frame_std, b1 - b0), 0, 1)
            rows.append(r)
        if f < frames - 1:
            rows += [base_row(gap_val) for _ in range(gap)]
    rows += [base_row(baffle_val) for _ in range(botb)]

    u16 = (np.array(rows) * 65535).astype(np.uint16)
    return u16 if channels == 1 else np.stack([u16] * 3, axis=2)


def test_detect_frames_synthetic_count_and_full_width_default():
    arr = _make_synthetic_strip(frames=6)
    H, W = arr.shape[:2]
    det = detect_frames(arr)
    assert det["long_axis"] == "y"
    boxes = det["boxes"]
    assert len(boxes) == 6, det
    # Projection band stays in the central film, clear of the sprockets (~30..170).
    p0, p1 = det["proj_band"]
    assert p0 >= 30 and p1 <= 170, det["proj_band"]
    # By default each frame keeps the entire short edge.
    for (x0, y0, x1, y1) in boxes:
        assert (x0, x1) == (0, W)
        assert (y1 - y0) >= 250
    # Head/tail preserved: first frame starts at the image top, last ends at the
    # image bottom (no cut facing the strip ends).
    assert boxes[0][1] == 0
    assert boxes[-1][3] == H


def test_detect_frames_head_tail_not_trimmed():
    """The outward edge of the first and last frames reaches the image border;
    only the interior frames are bounded by gaps on both sides."""
    arr = _make_synthetic_strip(frames=4)
    H = arr.shape[0]
    boxes = detect_frames(arr)["boxes"]
    assert boxes[0][1] == 0 and boxes[-1][3] == H
    # interior frames do not touch the image edges
    for (_, y0, _, y1) in boxes[1:-1]:
        assert y0 > 0 and y1 < H


def test_detect_frames_trim_baffle_drops_black_border():
    arr = _make_synthetic_strip(frames=4)
    W = arr.shape[1]
    full = detect_frames(arr)
    trimmed = detect_frames(arr, trim_baffle=True)
    # default spans the whole edge; trim_baffle pulls both edges inward (off baffle)
    assert full["boxes"][0][0] == 0 and full["boxes"][0][2] == W
    assert trimmed["boxes"][0][0] > 0 and trimmed["boxes"][0][2] < W


# --- robustness across film formats (synthetic; real samples still advised) ---

def test_detect_frames_120_no_sprockets():
    """120 medium format has no perforations: detection (central-band
    projection) must still work and the projection band must not collapse."""
    arr = _make_synthetic_strip(frames=6, sprockets=False, band_w=170)
    det = detect_frames(arr)
    assert len(det["boxes"]) == 6, det
    p0, p1 = det["proj_band"]
    assert p1 - p0 >= 50, det["proj_band"]   # non-degenerate central band


def test_detect_frames_black_and_white_grayscale():
    """Single-channel (B&W) scans split the same as color."""
    arr = _make_synthetic_strip(frames=5, channels=1)
    assert arr.ndim == 2
    det = detect_frames(arr)
    assert len(det["boxes"]) == 5, det


def test_detect_frames_longer_strip():
    arr = _make_synthetic_strip(frames=12)
    assert len(detect_frames(arr)["boxes"]) == 12


@pytest.mark.parametrize("fh", [140, 200, 300, 420])
def test_detect_frames_various_120_aspect_ratios(fh):
    """645 / 6x6 / 6x7 / 6x9 differ only in frame height along the strip; the
    pitch is derived from gaps, so the count is found regardless of aspect."""
    arr = _make_synthetic_strip(frames=4, fh=fh, sprockets=False, band_w=170)
    assert len(detect_frames(arr)["boxes"]) == 4


def _make_kelp_strip(specs, fh=270, gap=30, band_w=140, sprocket_w=15,
                     baffle_w=15, topb=40, botb=40, kelp_tail=0, seed=0):
    """Strip whose frames are individually 'normal' (textured), 'blank'
    (unexposed clear base: bright + smooth, identical to an inter-frame gap) or
    'black' (fully exposed: dark + smooth)."""
    rng = np.random.default_rng(seed)
    W = 2 * baffle_w + 2 * sprocket_w + band_w
    sl0, sl1 = baffle_w, baffle_w + sprocket_w
    b0, b1 = sl1, sl1 + band_w
    sr0, sr1 = b1, b1 + sprocket_w

    def base(fill):
        r = np.full(W, 0.10)
        r[sl0:sl1] = 0.90
        r[sr0:sr1] = 0.90
        r[b0:b1] = fill
        return r

    rows = [base(0.10) for _ in range(topb)]
    for k, spec in enumerate(specs):
        for _ in range(fh):
            r = base(0.45)
            if spec == "normal":
                r[b0:b1] = np.clip(rng.normal(0.45, 0.12, b1 - b0), 0, 1)
            elif spec == "blank":
                r[b0:b1] = 0.85
            elif spec == "black":
                r[b0:b1] = 0.05
            rows.append(r)
        if k < len(specs) - 1:
            rows += [base(0.85) for _ in range(gap)]
    # Optional gapless "kelp" stretch (uniform, fully-exposed mid-grey) directly
    # after the frames -- no inter-frame gap, mimics a dead section of film.
    rows += [base(0.40) for _ in range(kelp_tail)]
    rows += [base(0.10) for _ in range(botb)]
    return (np.array(rows) * 65535).astype(np.uint16)


def test_kelp_single_blank_frame_recovered():
    """A single unexposed (clear) frame mid-strip is still counted -- the pitch
    comes from the narrow gaps so the merged bright block can't corrupt it."""
    arr = _make_kelp_strip(["normal", "normal", "blank", "normal", "normal", "normal"])
    assert len(detect_frames(arr)["boxes"]) == 6


def test_kelp_fully_black_frames_detected():
    """Fully exposed (dark) frames split fine; regression for the std-floor fix
    (uniform bright gaps must not be crushed to zero score)."""
    arr = _make_kelp_strip(["black"] * 6)
    assert len(detect_frames(arr)["boxes"]) == 6


def test_kelp_all_blank_is_low_confidence():
    """An all-clear strip has no detectable boundaries -> flagged, not silently
    mis-split."""
    arr = _make_kelp_strip(["blank"] * 6)
    det = detect_frames(arr)
    assert det["low_confidence"] is True


def test_frames_override_forces_count():
    """--frames divides the long axis into N equal parts regardless of content
    (the escape hatch for ambiguous kelp strips)."""
    arr = _make_kelp_strip(["blank"] * 6)        # undetectable automatically
    det = detect_frames(arr, frames=6)
    assert len(det["boxes"]) == 6 and det["forced"] is True
    H = arr.shape[0]
    assert det["boxes"][0][1] == 0 and det["boxes"][-1][3] == H


def test_drop_kelp_discards_gapless_kelp_tail():
    """A real frame followed by a long gapless kelp stretch: --drop-kelp keeps
    only the textured frame and trims the kelp away."""
    arr = _make_kelp_strip(["normal"], kelp_tail=2400)
    keep = detect_frames(arr, drop_kelp=True)["boxes"]
    full = detect_frames(arr, drop_kelp=False)["boxes"]
    assert len(keep) == 1 and len(full) == 1
    # the kept frame is much shorter than the whole strip (kelp trimmed off)
    kept_h = keep[0][3] - keep[0][1]
    full_h = full[0][3] - full[0][1]
    assert kept_h < 0.6 * full_h


def test_drop_kelp_preserves_smooth_gap_bounded_frame():
    """A smooth (low-texture) but real frame bounded by inter-frame gaps must be
    kept under --drop-kelp -- it is not kelp."""
    specs = ["normal", "normal", "black", "normal", "normal", "normal"]
    assert len(detect_frames(_make_kelp_strip(specs), drop_kelp=True)["boxes"]) == 6


def test_detect_frames_fully_exposed_wide_sprockets():
    """Wide, fully-exposed bright sprocket bands must not break detection: the
    central projection band stays clear of them (no sprocket-pitch false gaps)."""
    arr = _make_synthetic_strip(frames=4, sprocket_w=40, sprocket_val=0.97)
    det = detect_frames(arr)
    assert len(det["boxes"]) == 4, det
    p0, _ = det["proj_band"]
    assert p0 >= 55, det["proj_band"]     # past baffle(15)+sprocket(40)


@pytest.fixture
def synthetic_strip_file(tmp_path):
    path = tmp_path / "strip.tif"
    tifffile.imwrite(str(path), _make_synthetic_strip(frames=6))
    return path


def test_split_cli_writes_frames(run_cli, synthetic_strip_file, output_dir):
    res = run_cli("tool", "split", "-i", str(synthetic_strip_file),
                  "-o", str(output_dir))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    written = sorted(output_dir.glob("frame_*.tif"))
    assert len(written) == 6
    # each output is a readable TIFF preserving 16-bit depth
    a = tifffile.imread(str(written[0]))
    assert a.dtype == np.uint16


def test_split_cli_dry_run_writes_nothing(run_cli, synthetic_strip_file, output_dir):
    res = run_cli("tool", "split", "-i", str(synthetic_strip_file),
                  "-o", str(output_dir), "--dry-run")
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert list(output_dir.glob("frame_*.tif")) == []
    # the JSON manifest line reports the detected count
    manifest = json.loads(res.stdout.strip().splitlines()[-1])
    assert manifest["frame_count"] == 6


def test_split_cli_rotate_swaps_dimensions(run_cli, synthetic_strip_file, output_dir):
    res = run_cli("tool", "split", "-i", str(synthetic_strip_file),
                  "-o", str(output_dir), "--rotate", "90")
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    a = tifffile.imread(str(sorted(output_dir.glob("frame_*.tif"))[0]))
    # rotated 90deg -> wider than tall (frame content is ~270 tall, band ~140 wide)
    assert a.shape[1] > a.shape[0]


def test_split_cli_input_missing(run_cli, output_dir, tmp_path):
    res = run_cli("tool", "split", "-i", str(tmp_path / "nope.tif"),
                  "-o", str(output_dir))
    assert res.returncode != 0
    assert list(output_dir.glob("frame_*.tif")) == []


def test_split_cli_missing_required_args(run_cli, output_dir):
    res = run_cli("tool", "split", "-o", str(output_dir))
    assert res.returncode != 0


@pytest.mark.slow
def test_split_cli_real_strip(run_cli, random_strip_input, output_dir):
    res = run_cli("tool", "split", "-i", str(random_strip_input),
                  "-o", str(output_dir))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert len(list(output_dir.glob("frame_*.tif"))) >= 2
