"""Algorithmic dust removal for film positives — no IR channel required.

Dust on a negative blocks light and, after the orange-mask inversion, becomes a
small, near-neutral *bright* spot. Without an infrared band we can only separate
dust from real image content heuristically, so this runs inside user-drawn ROIs
and every ROI gets its own robust statistics:

  * grain amplitude = MAD of the luminance high-pass (robust to the dust itself);
  * white top-hat   = L - medianBlur(L) keeps only small bright blobs;
  * two bands       = tophat >= t_dust  is dust (inpaint); the band between
                      t_grain..t_dust is grain (attenuated only on the fine end
                      of the 粗细 slider);
  * blob filters    = size / circularity / a-b neutrality keep coloured
                      highlights, stars and reflections out of the mask.

Only the masked pixels are written back so the rest of the float image keeps
full precision. The fine-end grain attenuation round-trips the ROI through 8-bit
Lab — acceptable for the prototype; production should shrink float detail
instead (see pr/024.dust.md, "修补").

Design: pr/024.dust.md
"""

import cv2
import numpy as np

_LAB_NEUTRAL = 128.0  # neutral point of a/b in 8-bit Lab


def _odd(v):
    return max(3, int(round(v)) | 1)


def _disk(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _slider_params(grain_level):
    """Map the 粗细 slider (0 fine/aggressive .. 1 coarse/conservative).

    fine  (->0): alpha -> 1 (flatten grain),  dust threshold -> 2.5x grain peak
    coarse(->1): alpha -> 0 (keep grain),     dust threshold -> 4.5x grain peak
    """
    g = float(np.clip(grain_level, 0.0, 1.0))
    alpha = max(0.0, 1.0 - g / 0.5)      # >= 0.5 → no grain flattening
    dust_gain = 2.5 + 2.0 * g            # dust must exceed grain amplitude × this
    return alpha, dust_gain


def remove_defects(img, regions, cfg):
    """Repair dust inside `regions` of a positive film image.

    img      (H, W, 3) float32 RGB, 0-1, post-inversion positive.
    regions  list of {shape:'rect', x1,y1,x2,y2, strength?} in img pixel coords.
             `strength` (None = follow global) is the per-ROI 粗细 override slot
             kept for the future "per-ROI strength" extension.
    cfg      {'grain_level': 0-1 global 粗细 slider, 'dust_size': px}.

    Returns a float32 copy. Pixels outside the ROIs — and, on the coarse end,
    everything except the dust mask — are bit-identical to the input.
    """
    out = np.array(img, dtype=np.float32, copy=True)
    grain_level = float(cfg.get("grain_level", 0.6))
    dust_size = int(cfg.get("dust_size", 9))

    for region in regions or []:
        if region.get("shape", "rect") != "rect":
            continue
        level = region.get("strength")
        _remove_dust_rect(
            out, region,
            float(level if level is not None else grain_level),
            dust_size,
        )
    return out


def detect_dust_mask(img, region, cfg):
    """Return the dust mask of one ROI (cropped to the ROI), for preview/debug.

    Same detection path as `remove_defects`; lets the UI highlight exactly which
    pixels will be repaired before the user commits.
    """
    h, w = img.shape[:2]
    dust_size = int(cfg.get("dust_size", 9))
    x1, y1 = max(0, int(region["x1"])), max(0, int(region["y1"]))
    x2, y2 = min(w, int(region["x2"])), min(h, int(region["y2"]))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None

    pad = max(2, dust_size // 2) + 2
    px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
    px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
    crop = img[py1:py2, px1:px2]
    if crop.shape[0] < 2 or crop.shape[1] < 2:
        return None

    a = _analyze(crop, dust_size, cfg.get("grain_level", 0.6))
    mask = a["mask"]
    ox1, oy1 = x1 - px1, y1 - py1
    return mask[oy1:oy1 + (y2 - y1), ox1:ox1 + (x2 - x1)]


def _analyze(crop, dust_size, grain_level):
    """Per-ROI diagnostics: Lab planes, noise floor, top-hat, thresholds, mask."""
    lab = cv2.cvtColor(
        (np.clip(crop, 0.0, 1.0) * 255.0).astype(np.uint8),
        cv2.COLOR_RGB2LAB,
    )
    L = lab[:, :, 0].astype(np.float32)
    A = lab[:, :, 1].astype(np.float32)
    B = lab[:, :, 2].astype(np.float32)

    # White top-hat against a median base: median removes small bright blobs
    # robustly, so the base is the local "typical" value — grain mostly cancels,
    # dust keeps its full contrast. (An opening base amplifies grain in textured
    # areas because it tracks the local minimum instead of the median.)
    k = _odd(dust_size)
    L_u8 = np.clip(np.round(L), 0, 255).astype(np.uint8)
    tophat = L - cv2.medianBlur(L_u8, k).astype(np.float32)

    # Grain amplitude = MAD of the luminance high-pass: robust to the very dust
    # we hunt (dust is rare, so the median is untouched). All thresholds scale
    # off it, so the algorithm adapts across ISO / film types automatically.
    hp = L - cv2.GaussianBlur(L, (0, 0), sigmaX=1.5)
    grain = float(1.4826 * np.median(np.abs(hp)))
    alpha, dust_gain = _slider_params(grain_level)
    t_grain = max(grain * 0.7, 3.0)
    t_dust = max(grain * dust_gain, 8.0)

    raw = (tophat >= t_dust).astype(np.uint8) * 255
    mask = _filter_components(raw, L, A, B, dust_size)

    return {
        "lab": lab, "L": L, "A": A, "B": B,
        "grain": grain, "tophat": tophat,
        "alpha": alpha, "t_grain": t_grain, "t_dust": t_dust, "mask": mask,
    }


def _remove_dust_rect(out, region, grain_level, dust_size):
    h, w = out.shape[:2]
    x1, y1 = max(0, int(region["x1"])), max(0, int(region["y1"]))
    x2, y2 = min(w, int(region["x2"])), min(h, int(region["y2"]))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return

    # Crop with a pad so inpainting at the ROI edge still has context.
    pad = max(2, dust_size // 2) + 2
    px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
    px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
    crop = out[py1:py2, px1:px2]
    if crop.shape[0] < 2 or crop.shape[1] < 2:
        return

    a = _analyze(crop, dust_size, grain_level)
    L, A, B, lab = a["L"], a["A"], a["B"], a["lab"]
    tophat, alpha, t_grain, mask = a["tophat"], a["alpha"], a["t_grain"], a["mask"]

    # Grain-band attenuation (fine end only).
    L_work = L - alpha * np.maximum(tophat - t_grain, 0.0)

    # Inpaint dust on the attenuated L and the original a/b planes.
    L_u8 = np.clip(np.round(L_work), 0, 255).astype(np.uint8)
    A_u8, B_u8 = lab[:, :, 1], lab[:, :, 2]
    if np.any(mask > 0):
        mask_d = cv2.dilate(mask, _disk(3), iterations=1)
        radius = max(2, dust_size // 2)
        L_u8 = cv2.inpaint(L_u8, mask_d, radius, cv2.INPAINT_TELEA)
        A_u8 = cv2.inpaint(A_u8, mask_d, radius, cv2.INPAINT_TELEA)
        B_u8 = cv2.inpaint(B_u8, mask_d, radius, cv2.INPAINT_TELEA)
    else:
        mask_d = None

    rgb_proc = cv2.cvtColor(
        cv2.merge([L_u8, A_u8, B_u8]), cv2.COLOR_LAB2RGB
    ).astype(np.float32) / 255.0

    if alpha > 0.0:
        # Grain flattening edits the whole ROI; write it all back.
        out[py1:py2, px1:px2] = rgb_proc
    elif mask_d is not None:
        # Coarse end: only repair the dust pixels, keep float precision elsewhere.
        m3 = (mask_d > 0).astype(np.float32)[..., None]
        out[py1:py2, px1:px2] = rgb_proc * m3 + crop * (1.0 - m3)
    # else: no dust, no flattening -> leave the ROI untouched.


def _filter_components(raw, L, A, B, dust_size):
    """Keep only blobs that look like dust: right size, round-ish, neutral.

    Drops grain clumps (too small), big soft blobs (too large), scratches
    (elongated — deferred feature), and anything coloured (real highlights,
    tinted reflections) via the a/b neutrality test.
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw, connectivity=8)
    if n <= 1:
        return np.zeros_like(raw)

    min_area = 4.0
    max_area = float(dust_size * dust_size)
    out = np.zeros_like(raw)

    for i in range(1, n):
        _, _, bw, bh, area = stats[i]
        if area < min_area or area > max_area:
            continue
        if bw > 3 * bh or bh > 3 * bw:
            continue

        ys, xs = np.where(labels == i)
        a_dev = float(np.mean(np.abs(A[ys, xs] - _LAB_NEUTRAL)))
        b_dev = float(np.mean(np.abs(B[ys, xs] - _LAB_NEUTRAL)))
        if a_dev > 28.0 or b_dev > 28.0:
            continue

        ab_std = float(np.std(A[ys, xs]) + np.std(B[ys, xs]))
        l_std = float(np.std(L[ys, xs]))
        if ab_std > 0.5 * (l_std + 1e-6):
            continue

        out[labels == i] = 255
    return out
