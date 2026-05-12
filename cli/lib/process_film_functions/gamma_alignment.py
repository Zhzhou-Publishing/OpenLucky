import math
import numpy as np


# Maximum absolute midtone shift per channel. Caps strong color casts so a
# single alignment pass can never push midtones past mild correction — the
# residual lives on for downstream LUTs / manual tuning to finish.
SHIFT_CAP = 0.20


def calculate_target_shifts(current_mids, user_ev_bias, mode):
    """Return per-channel midtone shift [Δr, Δg, Δb].

    Each Δ is the value added to its channel at x=0.5 (where the sin² mask
    peaks); the mask fades Δ smoothly to 0 at x=0 and x=1.
    """
    if mode == "ev_target":
        target_mid = 0.5 * math.pow(2, user_ev_bias * 0.33)
    elif mode == "green_base":
        target_mid = float(current_mids[1])
    elif mode == "highest_base":
        target_mid = float(np.max(current_mids))
    elif mode == "luminance_base":
        target_mid = (
            0.299 * current_mids[0] + 0.587 * current_mids[1] + 0.114 * current_mids[2]
        )
    else:
        target_mid = 0.5

    target_mid = max(0.01, min(0.99, target_mid))

    shifts = [float(target_mid - current_mids[i]) for i in range(3)]
    shifts = [max(-SHIFT_CAP, min(SHIFT_CAP, s)) for s in shifts]
    return shifts


def apply_midtone_alignment(
    img, roi=None, user_ev_bias=0.0, mode="green_base", protect_latitude=True
):
    """
    对图像执行自动中间调对齐（加法位移，非 gamma 变换）。

    与原 gamma 实现的关键区别：
    - 中间调位移幅度严格 = |target - cur|，不被 log/pow 放大
    - sin²(πx) 权重在端点处为 0，**斜率有限**，护栏可靠
    - 极端色偏时位移被 SHIFT_CAP 截断，不会把通道推出 [0,1]

    参数:
    - img: float32 RGB 图像 (0.0-1.0)
    - roi: 采样坐标 (x1, y1, x2, y2)
    - user_ev_bias: 拍摄意图 EV 偏置
    - mode: 对齐模式 ("ev_target", "green_base", "highest_base", "luminance_base")
    - protect_latitude: True 时位移按 sin² 权重作用于中间调；
        False 时全图直接加常量位移（端点也会被推动）。
    """
    h, w = img.shape[:2]

    # 1. 采样
    if roi is not None:
        x1, y1, x2, y2 = [int(round(c)) for c in roi]
        sample_area = img[max(0, y1) : min(h, y2), max(0, x1) : min(w, x2)]
        if sample_area.size == 0:
            sample_area = img
    else:
        sample_area = img

    pixels = sample_area.reshape(-1, 3)
    # Robust median: ignore pixels where any channel is pegged near 0 or 1
    # (specular highlights, AWB-clipped peaks, micro-specks of base/holder that
    # may have leaked through the ROI). Fall back to the raw sample if too few
    # pixels remain — better a slightly biased estimate than no estimate.
    interior_mask = (pixels.max(axis=1) < 0.95) & (pixels.min(axis=1) > 0.05)
    interior_count = int(interior_mask.sum())
    if interior_count >= max(64, int(pixels.shape[0] * 0.1)):
        pixels = pixels[interior_mask]
    current_mids = np.percentile(pixels, 50.0, axis=0)

    # 2. 计算每通道中间调位移
    shifts = calculate_target_shifts(current_mids, user_ev_bias, mode=mode)

    # 3. 应用位移
    for i in range(3):
        channel = img[:, :, i]
        if protect_latitude:
            mask = np.sin(np.clip(channel, 0.0, 1.0) * np.pi) ** 2
            img[:, :, i] = channel + shifts[i] * mask
        else:
            img[:, :, i] = channel + shifts[i]

    return np.clip(img, 0, 1.0)
