"""Algorithmic dust removal for film positives — no IR channel required.

Dust on a negative blocks light and, after the orange-mask inversion, becomes a
small bright spot. Real film dust is *not* neutral — it is yellowish (the
orange mask bleeds through) and forms soft, irregular clumps. pr/026 showed the
old "neutral bright spot" assumption + a/b-neutrality filter discarded real
dust as "coloured highlights", leaving the output unchanged.

The detector is now a LOCAL COLOUR ANOMALY: within a user-drawn ROI, a pixel is
dust when its Lab colour deviates from its neighbourhood (a large median) by
more than a threshold. Anything that stands out — yellow dust on skin, bright
dust on black cloth, even a coloured highlight — is treated as dust. Users are
told to keep ROIs small and avoid starfields / beach backgrounds, where real
content would be mistaken for anomalies.

  * local background = median blur large enough to swallow a dust clump;
  * anomaly          = Euclidean Lab distance from that local background;
  * mask             = anomaly >= threshold, filtered by size / elongation;
  * repair           = pull masked pixels back to the local background colour.

Only the masked pixels are written back so the rest of the float image keeps
full precision.

Design: pr/024.dust.md (original), pr/026.dust_colorful.md (rewrite rationale).
"""

import cv2
import numpy as np


def _odd(v):
    return max(3, int(round(v)) | 1)


def _disk(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _slider_params(grain_level):
    """Map the 粗细 slider (0 fine/aggressive .. 1 coarse/conservative).

    pr/026 rewrite: the slider now scales the colour-anomaly threshold gain.
    fine  (->0): low threshold — catch faint anomalies (small/soft dust);
    coarse(->1): high threshold — only strong, obvious anomalies.
    """
    g = float(np.clip(grain_level, 0.0, 1.0))
    anomaly_gain = 2.0 + 2.0 * g  # fine→2.0 (lenient), coarse→4.0 (strict)
    return anomaly_gain


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
    """Per-ROI diagnostics: Lab planes, local colour anomaly, thresholds, mask.

    pr/026.dust_colorful.md: real negative dust is NOT a neutral bright spot —
    it is a yellowish, irregular, soft clump. The old white top-hat + a/b
    neutrality test discarded it as a "coloured highlight". The detector is now
    a LOCAL COLOUR ANOMALY: a pixel is dust when its Lab colour deviates from
    its neighbourhood (a large median) by more than a threshold. Anything that
    stands out against its surroundings — yellow dust on skin, bright dust on
    black cloth, coloured highlights — is treated as dust. Users are told to
    keep ROIs small and avoid starfields/beach backgrounds.
    """
    lab = cv2.cvtColor(
        (np.clip(crop, 0.0, 1.0) * 255.0).astype(np.uint8),
        cv2.COLOR_RGB2LAB,
    )
    L = lab[:, :, 0].astype(np.float32)
    A = lab[:, :, 1].astype(np.float32)
    B = lab[:, :, 2].astype(np.float32)

    # Local background = a median large enough to swallow a dust clump. The
    # median (not mean) is robust to the anomaly itself, so the background stays
    # "typical neighbourhood colour" even under the dust.
    bg_k = _odd(max(dust_size * 3, 15))
    L_u8 = np.clip(np.round(L), 0, 255).astype(np.uint8)
    A_u8 = np.clip(np.round(A), 0, 255).astype(np.uint8)
    B_u8 = np.clip(np.round(B), 0, 255).astype(np.uint8)
    L_bg = cv2.medianBlur(L_u8, bg_k).astype(np.float32)
    A_bg = cv2.medianBlur(A_u8, bg_k).astype(np.float32)
    B_bg = cv2.medianBlur(B_u8, bg_k).astype(np.float32)

    # Anomaly distance = Euclidean colour deviation from the local background.
    dL = L - L_bg
    dA = A - A_bg
    dB = B - B_bg
    anomaly = np.sqrt(dL * dL + dA * dA + dB * dB)

    # Grain amplitude = MAD of the luminance high-pass, used as an adaptive
    # reference: on noisy (high-grain) frames the threshold rises so texture is
    # not mistaken for dust.
    hp = L - cv2.GaussianBlur(L, (0, 0), sigmaX=1.5)
    grain = float(1.4826 * np.median(np.abs(hp)))
    anomaly_gain = _slider_params(grain_level)

    # Anomaly threshold. A dust clump deviates ~25+ in Lab distance, while
    # grain/texture noise sits below ~15 (measured on real negatives — see
    # pr/026.dust_colorful.md). Scales with grain so noisy frames stay quiet.
    t_anomaly = max(grain * anomaly_gain, 20.0)

    raw = (anomaly >= t_anomaly).astype(np.uint8) * 255
    mask = _filter_components(raw, dust_size)

    return {
        "lab": lab, "L": L, "A": A, "B": B,
        "L_bg": L_bg, "A_bg": A_bg, "B_bg": B_bg,
        "anomaly": anomaly,
        "grain": grain, "t_anomaly": t_anomaly, "mask": mask,
    }


def _remove_dust_rect(out, region, grain_level, dust_size):
    h, w = out.shape[:2]
    x1, y1 = max(0, int(region["x1"])), max(0, int(region["y1"]))
    x2, y2 = min(w, int(region["x2"])), min(h, int(region["y2"]))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return

    # Crop with a pad so the background median at the ROI edge has context.
    pad = max(2, dust_size // 2) + 2
    px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
    px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
    crop = out[py1:py2, px1:px2]
    if crop.shape[0] < 2 or crop.shape[1] < 2:
        return

    a = _analyze(crop, dust_size, grain_level)
    lab, mask = a["lab"], a["mask"]
    L, A, B = a["L"], a["A"], a["B"]
    L_bg, A_bg, B_bg = a["L_bg"], a["A_bg"], a["B_bg"]

    if not np.any(mask > 0):
        return  # no anomaly in this ROI -> leave it untouched

    # Close to fill the hollow outline a large soft clump leaves behind, then
    # dilate slightly so the repair covers the anomaly's soft edge.
    mask_c = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _disk(max(3, dust_size // 2)))
    mask_d = cv2.dilate(mask_c, _disk(3), iterations=1)
    m3 = (mask_d > 0).astype(np.float32)[..., None]

    # Repair = pull each masked pixel's colour back to the local background
    # colour (median replacement). This matches the "soft clump with no hard
    # edge" real-dust shape better than Telea inpainting, which is designed for
    # isolated punctate spots.
    L_r = L * (1.0 - m3[..., 0]) + L_bg * m3[..., 0]
    A_r = A * (1.0 - m3[..., 0]) + A_bg * m3[..., 0]
    B_r = B * (1.0 - m3[..., 0]) + B_bg * m3[..., 0]
    rgb_proc = cv2.cvtColor(
        cv2.merge([
            np.clip(np.round(L_r), 0, 255).astype(np.uint8),
            np.clip(np.round(A_r), 0, 255).astype(np.uint8),
            np.clip(np.round(B_r), 0, 255).astype(np.uint8),
        ]),
        cv2.COLOR_LAB2RGB,
    ).astype(np.float32) / 255.0

    # Write back only the repaired pixels; the rest of the float crop keeps
    # full precision (unchanged).
    out[py1:py2, px1:px2] = rgb_proc * m3 + crop * (1.0 - m3)


def _filter_components(raw, dust_size):
    """Keep blobs of plausible dust size and shape (round-ish, not elongated).

    pr/026: the old a/b neutrality + colour-variance tests are GONE — they
    discarded real (yellowish) dust as "coloured highlights". The colour test
    now lives in _analyze's anomaly distance, so here we only gate on geometry:
    not a single-pixel grain clump, not a huge soft region, not a scratch.
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw, connectivity=8)
    if n <= 1:
        return np.zeros_like(raw)

    min_area = 3.0
    max_area = float((dust_size * 4) * (dust_size * 4))
    out = np.zeros_like(raw)

    for i in range(1, n):
        _, _, bw, bh, area = stats[i]
        if area < min_area or area > max_area:
            continue
        if bw > 4 * bh or bh > 4 * bw:
            continue

        out[labels == i] = 255
    return out
