"""Regression tests for 4-channel (RGB + infrared) scanner TIFFs.

Real film scanners emit 16-bit RGB scans with a 4th IR band (dust/scratch
removal) and often omit the ExtraSamples tag. The pipeline only needs RGB, so it
drops the 4th band on read. These tests are fast (tiny images) and always run —
they guard the drop-IR / correct-RGB / Unicode-path behaviour independently of
the larger @pytest.mark.slow sample-driven integration tests.
"""
import json

import cv2
import numpy as np
import tifffile

from cli.lib.tool.resize import drop_extra_channel, is_multichannel_tiff

# A known solid colour so we can assert RGB is preserved and NOT swapped, plus a
# distinct IR value that must never leak into the RGB output.
R, G, B, IR = 10000, 20000, 30000, 60000


def _write_rgbi(path, w=24, h=18):
    arr = np.zeros((h, w, 4), dtype=np.uint16)
    arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3] = R, G, B, IR
    tifffile.imwrite(str(path), arr, photometric="rgb", compression="deflate")
    return path


# --- pure-function unit tests --------------------------------------------------

def test_drop_extra_channel_drops_fourth_band():
    a = np.zeros((2, 2, 4), dtype=np.uint16)
    assert drop_extra_channel(a).shape == (2, 2, 3)


def test_drop_extra_channel_is_noop_for_rgb_and_gray():
    rgb = np.zeros((2, 2, 3), dtype=np.uint16)
    gray = np.zeros((2, 2), dtype=np.uint16)
    assert drop_extra_channel(rgb).shape == (2, 2, 3)
    assert drop_extra_channel(gray).shape == (2, 2)


def test_is_multichannel_tiff(tmp_path):
    four = _write_rgbi(tmp_path / "rgbi.tiff")
    three = tmp_path / "rgb.tiff"
    tifffile.imwrite(str(three), np.zeros((4, 4, 3), dtype=np.uint16), photometric="rgb")
    png = tmp_path / "x.png"
    cv2.imwrite(str(png), np.zeros((4, 4, 3), dtype=np.uint8))
    assert is_multichannel_tiff(four) is True
    assert is_multichannel_tiff(three) is False
    assert is_multichannel_tiff(png) is False


# --- CLI integration tests -----------------------------------------------------

def test_resize_drops_ir_and_keeps_rgb(run_cli, tmp_path, output_dir):
    src = _write_rgbi(tmp_path / "scan.tiff")
    out = output_dir / "scan.tiff"
    res = run_cli("tool", "resize", "-i", str(src), "-o", str(out),
                  "--mode", "fixed-value", "--edge", "long-edge", "--value", "12")
    assert res.returncode == 0, res.stdout + res.stderr
    img = tifffile.imread(str(out))  # tifffile → native RGB order
    assert img.ndim == 3 and img.shape[2] == 3, f"IR not dropped: {img.shape}"
    # Solid colour survives INTER_AREA unchanged; RGB order intact, IR gone.
    assert list(img[0, 0]) == [R, G, B]


def test_resize_copy_path_drops_ir(run_cli, tmp_path, output_dir):
    """No -v on a 4-channel TIFF still yields a clean 3-channel RGB copy."""
    src = _write_rgbi(tmp_path / "scan.tiff")
    out = output_dir / "scan.tiff"
    res = run_cli("tool", "resize", "-i", str(src), "-o", str(out))
    assert res.returncode == 0, res.stdout + res.stderr
    img = tifffile.imread(str(out))
    assert img.shape[2] == 3
    assert img.shape[:2] == (18, 24)  # full-res, only IR removed
    assert list(img[0, 0]) == [R, G, B]


def test_tiff2jpeg_handles_four_channel(run_cli, tmp_path, output_dir):
    """Exports without the IR-as-alpha darkening and without the GBK emoji crash."""
    src = _write_rgbi(tmp_path / "scan.tiff")
    out = output_dir / "out.jpg"
    res = run_cli("tiff2jpeg", "-i", str(src), "-o", str(out))
    assert res.returncode == 0, res.stdout + res.stderr
    assert out.exists() and out.stat().st_size > 0
    px = cv2.cvtColor(cv2.imread(str(out)), cv2.COLOR_BGR2RGB)[0, 0]
    # 16-bit → 8-bit, IR dropped (not flattened); ~[39, 78, 117]. Allow JPEG slack.
    assert abs(int(px[0]) - R // 257) <= 4
    assert abs(int(px[2]) - B // 257) <= 4


def test_pick_returns_rgb_without_ir(run_cli, tmp_path):
    src = _write_rgbi(tmp_path / "scan.tiff")
    res = run_cli("tool", "pick", "-i", str(src), "-x", "1", "-y", "1", "-f", "16")
    assert res.returncode == 0, res.stdout + res.stderr
    data = json.loads(res.stdout)
    assert data["rgb"] == [R, G, B]


def test_histogram_handles_cjk_path_and_four_channel(run_cli, tmp_path):
    """Guards the read_image_safe switch: CJK folder + 4-channel 16-bit TIFF."""
    cjk_dir = tmp_path / "02 猫煞"
    cjk_dir.mkdir()
    src = _write_rgbi(cjk_dir / "测试.tiff", w=40, h=40)
    res = run_cli("tool", "histogram", "-i", str(src), "-d", "256", "-m", "linear")
    assert res.returncode == 0, res.stdout + res.stderr
    payload = json.loads(res.stdout)
    assert set(payload["data"]) == {"red", "green", "blue", "luminosity"}
