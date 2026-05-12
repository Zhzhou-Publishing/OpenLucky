"""Image histogram computation tool.

Computes per-channel histograms (and a luminance channel for the rgbl
type) with optional gamma correction and X-axis bin downsampling.

Output schema:

    {
        "data": { "red": [...], "green": [...], "blue": [...], "luminosity": [...] },
        "visual_meta": {
            "suggested_max_y": <int>,   # y-axis ceiling in the same unit as data
            "is_clipped": <bool>,       # significant pile-up at first/last bin
            "total_pixels": <int>       # pixels histogrammed (post-area-crop)
        }
    }

`data` values are in the transformed space chosen by `mode`:
  - mode="log"    → log1p(count) per bin
  - mode="linear" → raw count per bin

The renderer scales each value by `suggested_max_y` to fit the canvas:
    py = canvas_h * (1 - value / suggested_max_y)
"""

import math
from pathlib import Path

import cv2
import numpy as np
import rawpy

SUPPORTED_TYPES = {"rgbl"}
SUPPORTED_MODES = {"log", "linear"}

# ITU-R BT.601 luma coefficients
BT601_R = 0.299
BT601_G = 0.587
BT601_B = 0.114

# Headroom multipliers applied to the interior-bin peak when choosing the
# y-axis ceiling. Log mode is already compressed so a small margin suffices.
LOG_HEADROOM = 1.05
LINEAR_HEADROOM = 1.1
# Lower floor for linear mode so near-empty histograms still look reasonable.
LINEAR_FLOOR_RATIO = 0.005
# End-bin pile-up multiple that triggers the `is_clipped` flag.
CLIP_RATIO = 1.5


def _is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def validate_downsampling(downsampling):
    if downsampling is None:
        return None
    if not isinstance(downsampling, int) or isinstance(downsampling, bool):
        raise ValueError(
            f"Invalid downsampling value. Expected integer, got {downsampling!r}"
        )
    if not (256 <= downsampling <= 65536):
        raise ValueError(
            f"Invalid downsampling value. Expected integer in [256, 65536], got {downsampling}"
        )
    if not _is_power_of_two(downsampling):
        raise ValueError(
            f"Invalid downsampling value. Expected power of 2, got {downsampling}"
        )
    return downsampling


def _smooth_histogram(hist_data):
    """3点高斯平滑，消除梳齿，提升视觉高级感"""
    if len(hist_data) < 3:
        return hist_data
    kernel = np.array([0.25, 0.5, 0.25])
    return np.convolve(hist_data.astype(np.float64), kernel, mode="same")


def apply_gamma(channel, gamma, max_val):
    """Apply gamma encoding y = x^(1/gamma) on a 0..max_val channel."""
    if gamma is None or gamma == 1:
        return channel
    if gamma <= 0:
        raise ValueError(f"Invalid gamma value. Expected positive number, got {gamma}")
    norm = channel.astype(np.float64) / max_val
    encoded = np.power(np.clip(norm, 0, 1), 1.0 / gamma)
    return (encoded * max_val).astype(channel.dtype)


def compute_channel_histogram(channel, native_bins, downsampling):
    """Histogram a single channel at native_bins; collapse with max() to downsampling if smaller."""
    hist, _ = np.histogram(channel, bins=native_bins, range=(0, native_bins))

    if downsampling is None or downsampling >= native_bins:
        return _smooth_histogram(hist)

    reshaped = hist.reshape(downsampling, -1)
    hist = np.max(reshaped, axis=1)
    return _smooth_histogram(hist)


def load_image_for_histogram(input_path):
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    ext = input_path.suffix.lower()
    raw_exts = {".arw", ".cr2", ".nef", ".dng", ".raf"}

    if ext in raw_exts:
        with rawpy.imread(str(input_path)) as raw:
            img = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=16,
                bright=1.0,
            )
        return img

    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Failed to read image: {input_path}")

    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.ndim == 3 and img.shape[2] >= 3:
        img = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2RGB)

    return img


def compute_histogram(
    input_path,
    hist_type="rgbl",
    gamma=1.0,
    mode="log",
    downsampling=None,
    area=None,
):
    if hist_type not in SUPPORTED_TYPES:
        raise ValueError(f"Invalid type. Got '{hist_type}'")
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Invalid mode. Got '{mode}'")

    downsampling = validate_downsampling(downsampling)

    img = load_image_for_histogram(input_path)

    if area is not None:
        x1, y1, x2, y2 = area
        h_img, w_img = img.shape[:2]
        x1c = max(0, min(w_img, int(x1)))
        x2c = max(0, min(w_img, int(x2)))
        y1c = max(0, min(h_img, int(y1)))
        y2c = max(0, min(h_img, int(y2)))
        if x2c <= x1c or y2c <= y1c:
            raise ValueError(
                f"Invalid --area: empty intersection (image {w_img}x{h_img}, area={area})"
            )
        img = img[y1c:y2c, x1c:x2c]

    total_pixels = int(img.shape[0] * img.shape[1])

    if img.dtype == np.uint16:
        native_bins, max_val = 65536, 65535
    else:
        if img.dtype != np.uint8:
            img = np.clip(img, 0, 255).astype(np.uint8)
        native_bins, max_val = 256, 255

    if gamma != 1:
        img = apply_gamma(img, gamma, max_val)

    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    l_float = (
        BT601_R * r.astype(np.float64)
        + BT601_G * g.astype(np.float64)
        + BT601_B * b.astype(np.float64)
    )
    l = np.clip(l_float, 0, max_val).astype(img.dtype)

    raw_hists = [
        compute_channel_histogram(ch, native_bins, downsampling)
        for ch in [r, g, b, l]
    ]

    # End-bin pile-up detection runs on raw counts (independent of mode), so
    # the flag means "shadows or highlights are clipping," not "the line just
    # exits the canvas."
    is_clipped = False
    for h in raw_hists:
        if len(h) > 2:
            interior_peak = float(np.max(h[1:-1]))
            if interior_peak > 0 and (
                float(h[0]) > interior_peak * CLIP_RATIO
                or float(h[-1]) > interior_peak * CLIP_RATIO
            ):
                is_clipped = True
                break

    if mode == "log":
        transformed = [np.log1p(h.astype(np.float64)) for h in raw_hists]
        headroom = LOG_HEADROOM
    else:
        transformed = [h.astype(np.float64) for h in raw_hists]
        headroom = LINEAR_HEADROOM

    interior_max = 0.0
    for h in transformed:
        if len(h) > 2:
            interior_max = max(interior_max, float(np.max(h[1:-1])))
        else:
            interior_max = max(interior_max, float(np.max(h)))

    suggested_max_y = interior_max * headroom
    if mode == "linear":
        suggested_max_y = max(suggested_max_y, total_pixels * LINEAR_FLOOR_RATIO)

    # Keep two decimals: log-mode peaks land around 7-15 for typical photos,
    # so integer rounding collapses adjacent bins to the same step and the
    # rendered polyline looks like a square wave.
    data_output = [np.round(h, 2).tolist() for h in transformed]
    suggested_max_y_int = max(1, int(math.ceil(suggested_max_y)))

    return {
        "data": {
            "red": data_output[0],
            "green": data_output[1],
            "blue": data_output[2],
            "luminosity": data_output[3],
        },
        "visual_meta": {
            "suggested_max_y": suggested_max_y_int,
            "is_clipped": is_clipped,
            "total_pixels": total_pixels,
        },
    }
