"""Image histogram computation tool.

Computes per-channel histograms (and a luminance channel for the rgbl
type) with optional gamma correction, log/linear normalization, and
X-axis bin downsampling. Designed for UI consumption.
"""
from pathlib import Path

import cv2
import numpy as np
import rawpy

from cli.constants.image_formats import IMAGE_EXTENSIONS, RAW_EXTENSIONS
from cli.lib.tool.resize import read_image_safe


SUPPORTED_TYPES = {'rgbl'}
SUPPORTED_MODES = {'log', 'linear'}

# ITU-R BT.601 luma coefficients
BT601_R = 0.299
BT601_G = 0.587
BT601_B = 0.114


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


def normalize_linear(hist_data, normalization):
    """Linear scale to [0, normalization]; non-zero bins are floored to at least 1."""
    max_val = np.max(hist_data)
    if max_val == 0:
        return np.zeros_like(hist_data, dtype=np.int32)
    normalized = (hist_data.astype(np.float64) / max_val) * normalization
    normalized[(hist_data > 0) & (normalized < 1)] = 1
    return normalized.astype(np.int32)


def normalize_log(hist_data, normalization):
    """log1p scale to [0, normalization]."""
    log_data = np.log1p(hist_data.astype(np.float64))
    max_log = np.max(log_data)
    if max_log == 0:
        return np.zeros_like(hist_data, dtype=np.int32)
    normalized = (log_data / max_log) * normalization
    return normalized.astype(np.int32)


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
    hist, _ = np.histogram(channel, bins=native_bins, range=(0, native_bins - 1))
    if downsampling is None or downsampling >= native_bins:
        return hist
    reshaped = hist.reshape(downsampling, -1)
    return np.max(reshaped, axis=1)


def load_image_for_histogram(input_path):
    """Load an image as an RGB array. RAW gets demosaiced to 16-bit linear RGB."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    ext = input_path.suffix.lower()
    if ext in RAW_EXTENSIONS:
        with rawpy.imread(str(input_path)) as raw:
            img = raw.postprocess(
                demosaic_algorithm=(
                    rawpy.DemosaicAlgorithm.DHT if ext == '.raf'
                    else rawpy.DemosaicAlgorithm.AAHD
                ),
                fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                gamma=(1, 1),
                no_auto_bright=True,
                output_bps=16,
                use_camera_wb=True,
                bright=1.0,
            )
        return img

    if ext not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {ext}")

    img = read_image_safe(str(input_path))
    if img is None:
        raise ValueError(f"Failed to read image: {input_path}")

    if img.ndim == 2:
        img = np.stack([img, img, img], axis=-1)
    elif img.ndim == 3 and img.shape[2] >= 3:
        img = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2RGB)
    else:
        raise ValueError(f"Unsupported image shape {img.shape} for histogram")
    return img


def compute_histogram(input_path, hist_type='rgbl', gamma=1.0,
                     mode='log', normalization=None, downsampling=None):
    """Compute histogram per pr/020.histogram.md.

    Returns a 2-D list of ints. Outer length depends on hist_type
    (rgbl → 4, ordered R, G, B, L). Inner length is `downsampling`
    when set, otherwise the native bin count of the source image
    (256 for 8-bit, 65536 for 16-bit).
    """
    if hist_type not in SUPPORTED_TYPES:
        raise ValueError(
            f"Invalid type. Expected one of {sorted(SUPPORTED_TYPES)}, got '{hist_type}'"
        )
    if mode not in SUPPORTED_MODES:
        raise ValueError(
            f"Invalid mode. Expected one of {sorted(SUPPORTED_MODES)}, got '{mode}'"
        )
    downsampling = validate_downsampling(downsampling)
    if normalization is not None:
        if not isinstance(normalization, int) or isinstance(normalization, bool) or normalization <= 0:
            raise ValueError(
                f"Invalid normalization value. Expected positive integer, got {normalization!r}"
            )

    img = load_image_for_histogram(input_path)

    if img.dtype == np.uint16:
        native_bins = 65536
        max_val = 65535
    else:
        if img.dtype != np.uint8:
            img = np.clip(img, 0, 255).astype(np.uint8)
        native_bins = 256
        max_val = 255

    if gamma != 1:
        img = apply_gamma(img, gamma, max_val)

    if hist_type == 'rgbl':
        r = img[:, :, 0]
        g = img[:, :, 1]
        b = img[:, :, 2]
        l_float = (
            BT601_R * r.astype(np.float64)
            + BT601_G * g.astype(np.float64)
            + BT601_B * b.astype(np.float64)
        )
        l = np.clip(l_float, 0, max_val).astype(img.dtype)
        channels = [r, g, b, l]
    else:
        channels = []

    raw_hists = [compute_channel_histogram(ch, native_bins, downsampling) for ch in channels]

    if normalization is None:
        return [h.astype(np.int64).tolist() for h in raw_hists]

    if mode == 'log':
        normalized = [normalize_log(h, normalization) for h in raw_hists]
    else:
        normalized = [normalize_linear(h, normalization) for h in raw_hists]

    return [h.tolist() for h in normalized]
