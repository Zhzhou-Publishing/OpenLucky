"""Image color picker tool.

Reads a single pixel value from a TIFF / RAW / bitmap at (x, y) and emits
JSON. Used by the desktop eyedropper to retrieve the source-truth color
of a pixel that's only being displayed via a lossy JPEG preview.
"""
from pathlib import Path

import cv2
import numpy as np
import rawpy

from cli.constants.image_formats import IMAGE_EXTENSIONS, RAW_EXTENSIONS
from cli.lib.tool.resize import read_image_safe


SUPPORTED_FORMATS = {'8', '16'}


def load_image_for_pick(input_path):
    """Load image as RGB ndarray (uint8 or uint16). Mirrors the histogram path."""
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
        return img, True

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
        raise ValueError(f"Unsupported image shape {img.shape}")

    return img, False


def pick_color(input_path, x, y, output_format='8'):
    """Return the color at (x, y) in the requested bit depth.

    Args:
        input_path: image file path
        x, y: 0-indexed pixel coordinates
        output_format: '8' or '16'

    Returns:
        dict with rgb / bit_depth / coords / dimensions / is_raw
    """
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Invalid format. Expected one of {sorted(SUPPORTED_FORMATS)}, got '{output_format}'"
        )
    if not isinstance(x, int) or not isinstance(y, int) or isinstance(x, bool) or isinstance(y, bool):
        raise ValueError(f"Coordinates must be integers, got x={x!r}, y={y!r}")
    if x < 0 or y < 0:
        raise ValueError(f"Coordinates must be non-negative, got x={x}, y={y}")

    img, is_raw = load_image_for_pick(input_path)
    height, width = img.shape[:2]

    if x >= width or y >= height:
        raise ValueError(
            f"Coordinates out of range: ({x}, {y}) for image {width}x{height}"
        )

    pixel = img[y, x]
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])

    if img.dtype == np.uint16:
        if output_format == '8':
            rgb = [int(round(c / 257)) for c in (r, g, b)]
        else:
            rgb = [r, g, b]
    else:
        if output_format == '16':
            rgb = [c * 257 for c in (r, g, b)]
        else:
            rgb = [r, g, b]

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "rgb": rgb,
        "bit_depth": int(output_format),
        "is_raw": is_raw,
    }
