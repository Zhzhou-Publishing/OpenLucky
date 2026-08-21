"""Density-domain film inversion helpers (the v2 engine).

Pure, vectorised numpy functions used by the v2 pipeline in
``process_film.py`` (see design/film-color-v2.md).

Working domain: linear-light transmission ``0..1`` becomes optical density
``-log10(T)``. A color mask (orange base) is *multiplicative* in transmission
but *additive* in density, so it is removed by subtraction, not division.
Per-channel D-min/D-max normalization then both inverts the negative and
restores each channel's dynamic range independently — this is the main colour
accuracy win over the linear-domain ``1 - x`` pipeline.

All functions are pure (no I/O) and operate on float32 (H, W, 3) arrays unless
noted otherwise.
"""

import numpy as np

# Floor used before log10 so the transmission never collapses to -inf.
EPSILON = 1e-6

# Status M decross-talk matrix — currently DIAGONAL: cross terms are zeroed so
# the pipeline does no crosstalk correction yet (per-channel density scaling
# only).
# Row-major layout: row = output channel, column = input channel.
STATUS_M = np.array(
    [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ],
    dtype=np.float32,
)

# Rec.709 / linear-sRGB luminance weights — the fixed density-capture domain.
DENSITY_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

# Density domain assumed by the endpoint estimation (d in [-1, 3]).
DENSITY_RANGE = (-1.0, 3.0)


def to_density(linear_rgb):
    """linear transmission 0..1 -> optical density, per channel."""
    return -np.log10(np.maximum(linear_rgb, EPSILON))


def from_density(density):
    """optical density -> linear transmission."""
    return np.power(10.0, -density)


def mask_to_density(mask_0_255):
    """0..255 mask values -> density vector (length 3 or broadcastable)."""
    arr = np.asarray(mask_0_255, dtype=np.float32)
    return -np.log10(np.maximum(arr / 255.0, EPSILON))


def subtract_mask(density, mask_density):
    """Remove the base mask in density space (additive in log domain)."""
    return density - mask_density


def decrosstalk(density, matrix=None, enabled=True):
    """Apply the Status M decross-talk matrix in density space.

    matrix is row-major; ``density @ matrix.T`` multiplies each output channel
    by the corresponding matrix row. Defaults to STATUS_M. Disable to bypass.
    """
    if not enabled:
        return density
    m = STATUS_M if matrix is None else np.asarray(matrix, dtype=np.float32)
    return density @ m.T


def density_luma(density):
    """Rec.709 luma of a density vector/image (used by BW merging)."""
    return np.tensordot(density, DENSITY_LUMA, axes=1)


def auto_base_mask(linear_rgb):
    """Estimate the base (film mask) from the brightest pixels.

    Each channel's 99th percentile is treated as the base transmission.
    Returns a 3-vector in 0..255 suitable for feeding mask_to_density.
    Fallback only — an eyedropper sample of the actual film base is always
    preferred (device dependent).
    """
    arr = np.asarray(linear_rgb, dtype=np.float32).reshape(-1, 3)
    base_t = np.percentile(arr, 99.0, axis=0)
    return (np.clip(base_t, 0.0, 1.0) * 255.0).astype(np.float32)


def estimate_density_limits(density, roi=None, spike_threshold=0.10, tail=0.01,
                            spike_guard=0.20, bins=65536):
    """Per-channel D-min/D-max from a density histogram with spike guard.

    Histogram spikes (a bin holding > spike_threshold of the total) are skipped
    while the running accumulation is still below spike_guard, then the tail /
    (1 - tail) percentile defines the endpoint. This keeps large dead-white /
    dead-black regions (borders, film base, scanner edges) from stealing the
    endpoints.

    density: (H, W, 3) or (N, 3) density image.
    roi: optional (x1, y1, x2, y2) sample window in density's coordinates;
         None samples the whole image.
    Returns (d_min, d_max), each a float32 length-3 array.
    """
    arr = np.asarray(density, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr[None, :]  # (3,) -> (1, 3)
    h, w = arr.shape[:2]
    if roi is not None:
        x1, y1, x2, y2 = [int(round(c)) for c in roi]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 > x1 and y2 > y1:
            sample = arr[y1:y2, x1:x2].reshape(-1, 3)
        else:
            sample = arr.reshape(-1, 3)
    else:
        sample = arr.reshape(-1, 3)

    d_min = np.empty(3, dtype=np.float32)
    d_max = np.empty(3, dtype=np.float32)
    for c in range(3):
        d_min[c] = _density_endpoint(sample[:, c], high=False, spike_threshold=spike_threshold,
                                     tail=tail, spike_guard=spike_guard, bins=bins)
        d_max[c] = _density_endpoint(sample[:, c], high=True, spike_threshold=spike_threshold,
                                     tail=tail, spike_guard=spike_guard, bins=bins)
    return d_min, d_max


def _density_endpoint(samples, high, spike_threshold, tail, spike_guard, bins):
    """Density histogram endpoint (low or high), skipping early spikes.

    Spikes (a bin > spike_threshold of total) are skipped while the running
    accumulation is below spike_guard. If the guard skips *everything* (a
    single-spike degenerate image, or all spikes), fall back to the plain
    tail percentile so the endpoint stays finite and useful.
    """
    hist, edges = np.histogram(samples, bins=bins, range=DENSITY_RANGE)
    counts = hist.astype(np.float64)
    total = counts.sum()
    if total == 0:
        return 0.0
    threshold = total * spike_threshold
    guard = total * spike_guard
    target = total * tail
    accumulated = 0.0
    index_range = range(len(counts) - 1, -1, -1) if high else range(len(counts))
    endpoint = None
    for i in index_range:
        cnt = counts[i]
        if cnt > threshold and accumulated < guard:
            continue
        accumulated += cnt
        if accumulated >= target:
            endpoint = edges[i + 1] if high else edges[i]
            break
    if endpoint is None:
        p = (1.0 - tail) * 100.0 if high else tail * 100.0
        endpoint = float(np.percentile(samples, p))
    return endpoint


def normalize_density(density, d_min, d_max):
    """(d - d_min) / (d_max - d_min) per channel, degenerate-range guarded.

    High density (exposed negative = scene highlight) maps toward 1 (bright in
    the positive); low density (base / scene shadow) maps toward 0 (dark). The
    normalization itself is the inversion — no separate ``1 - x``.
    """
    d_min = np.asarray(d_min, dtype=np.float32)
    d_max = np.asarray(d_max, dtype=np.float32)
    rng = d_max - d_min
    safe = np.where(np.abs(rng) > 1e-6, rng, 1.0)
    return (density - d_min) / safe


def srgb_to_linear(encoded_rgb):
    """Decode sRGB-encoded 0..1 values to linear light (decision 4, not wired).

    Non-RAW inputs (JPEG/scanner TIFF) are currently treated as linear by v1.
    When decision 4 lands as its own milestone this becomes the v2 default for
    non-RAW input; raw_to_tiff output (gamma=(1,1)) must stay linear, so the
    call site decides, not this function.
    """
    arr = np.asarray(encoded_rgb, dtype=np.float32)
    low = arr <= 0.04045
    out = np.where(low, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def linear_to_srgb(linear_rgb):
    """Encode linear 0..1 to sRGB (inverse of srgb_to_linear)."""
    arr = np.asarray(linear_rgb, dtype=np.float32)
    low = arr <= 0.0031308
    out = np.where(low, arr * 12.92, 1.055 * arr ** (1.0 / 2.4) - 0.055)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def apply_post_gamma_adjustments(rgb, highlights=0.0, shadows=0.0, saturation=0.0,
                                 temperature=0.0, tint=0.0,
                                 luma_coefficients=DENSITY_LUMA):
    """Creative colour controls applied after gamma.

    - temperature, tint, saturation are offsets in [-1, 1] (0 = neutral).
    - temperature>0 warms: R up, B down.
    - tint>0 pushes magenta: R & B up, G down.
    - saturation is a deviation from 1.0 (1.15x preset -> +0.15).
    """
    adjusted = np.asarray(rgb, dtype=np.float32).copy()

    temperature = float(np.clip(temperature, -1.0, 1.0))
    adjusted[..., 0] *= 1.0 + temperature * 0.20
    adjusted[..., 2] *= 1.0 - temperature * 0.20

    tint = float(np.clip(tint, -1.0, 1.0))
    adjusted[..., 0] *= 1.0 + tint * 0.10
    adjusted[..., 1] *= 1.0 - tint * 0.20
    adjusted[..., 2] *= 1.0 + tint * 0.10

    luma = adjusted @ np.asarray(luma_coefficients, dtype=np.float32)
    saturation_factor = 1.0 + float(np.clip(saturation, -1.0, 1.0))
    out = luma[..., None] + (adjusted - luma[..., None]) * saturation_factor
    return np.clip(out, 0.0, 1.0).astype(np.float32)
