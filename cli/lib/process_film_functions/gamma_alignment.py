import math
import numpy as np

# Gamma clipping range — narrowed to prevent extreme hue shifts.
# Original [0.4, 2.5] was too permissive for the log(cur)/log(target) formula,
# allowing R-darkening + B-lightening that turned skin tones purple/magenta.
GAMMA_CLIP_MIN = 0.7
GAMMA_CLIP_MAX = 1.4


def calculate_auto_alignment_gamma(current_mids, user_ev_bias=0.0, mode="ev_target",
                                    strength=0.6, skin_protection=True):
    """
    计算自动对齐的 Gamma 增益值

    参数:
    - current_mids: 每通道中位数 [R, G, B]
    - user_ev_bias: 拍摄意图 EV 偏置（仅在 mode='ev_target' 时生效）
    - mode: 对齐模式 ("ev_target", "green_base", "highest_base", "luminance_base")
    - strength: 0.0-1.0，校正强度。1.0=完整校正，0.0=恒等（所有 gamma=1.0）
    - skin_protection: 是否启用肤色保护。暖调场景下进一步约束 R↓ 和 B↑，
        防止肤色偏紫/洋红，同时不影响冷调场景的正常去色罩校正。
    """
    if mode == "ev_target":
        target_mid = 0.5 * math.pow(2, user_ev_bias * 0.33)
    elif mode == "green_base":
        target_mid = current_mids[1]
    elif mode == "highest_base":
        target_mid = np.max(current_mids)
    elif mode == "luminance_base":
        target_mid = (
            0.299 * current_mids[0] + 0.587 * current_mids[1] + 0.114 * current_mids[2]
        )
    else:
        target_mid = 0.5

    target_mid = max(0.01, min(0.99, target_mid))

    # 1. Compute raw per-channel gamma values with narrower clipping
    gains_gamma = []
    for i in range(3):
        cur = max(current_mids[i], 1e-6)
        try:
            g = math.log(cur) / math.log(target_mid)
        except (ZeroDivisionError, ValueError):
            g = 1.0
        gains_gamma.append(max(GAMMA_CLIP_MIN, min(GAMMA_CLIP_MAX, g)))

    # 2. Blend gamma gains toward 1.0 (identity) by strength
    #    g = 1.0 + (g - 1.0) * strength
    #    strength=1.0 → full correction; strength=0.0 → identity
    if strength < 1.0:
        for i in range(3):
            gains_gamma[i] = 1.0 + (gains_gamma[i] - 1.0) * strength

    # 3. Skin protection: warm scenes (R_med > G_med) get additional
    #    constraint on the specific R-darkening + B-lightening combination
    #    that causes skin tones to shift toward purple/magenta.
    #    Cool scenes (R_med < G_med) are NOT affected — R↑ + B↓ is
    #    legitimate color-cast correction that should be preserved.
    if skin_protection:
        r_med, g_med = (
            float(current_mids[0]),
            float(current_mids[1]),
        )
        if r_med > g_med:
            # Warm scene detected: compute relative warmth
            warmth = (r_med - g_med) / max(g_med, 0.01)
            # Protection factor: 0=no extra protection, 1=full protection
            spf = min(1.0, warmth / 0.15)

            # Red: prevent darkening (gamma < 1.0 darkens the channel)
            if gains_gamma[0] < 1.0:
                gains_gamma[0] = 1.0 + (gains_gamma[0] - 1.0) * (1.0 - spf * 0.5)

            # Blue: prevent lightening (gamma > 1.0 lightens the channel)
            if gains_gamma[2] > 1.0:
                gains_gamma[2] = 1.0 + (gains_gamma[2] - 1.0) * (1.0 - spf * 0.5)

    return gains_gamma


def apply_gamma_alignment(
    img, roi=None, user_ev_bias=0.0, mode="green_base",
    protect_latitude=True, strength=0.6, skin_protection=True,
):
    """
    对图像执行自动 Gamma 对齐

    参数:
    - img: float32 RGB 图像 (0.0-1.0)
    - roi: 采样坐标 (x1, y1, x2, y2)
    - user_ev_bias: 拍摄意图 EV 偏置
    - mode: 对齐模式 ("ev_target", "green_base", "highest_base", "luminance_base")
    - protect_latitude: 宽容度保护开关。
        开启后，Gamma 变换将主要作用于中间调，保护高光和阴影不被过度拉伸/挤压。
    - strength: 0.0-1.0，校正强度。1.0=完整校正，0.0=恒等。
    - skin_protection: 肤色保护。暖调场景下限制 R↓ B↑ 防止肤色偏紫。
    """
    h, w = img.shape[:2]

    # 1. 采样与计算中位数
    # roi 可能是 (None, None, None, None)（未指定白点区域时），需同时排除，
    # 否则 round(None) 抛 TypeError。
    if roi is not None and all(c is not None for c in roi):
        x1, y1, x2, y2 = [int(round(c)) for c in roi]
        sample_area = img[max(0, y1) : min(h, y2), max(0, x1) : min(w, x2)]
        if sample_area.size == 0:
            sample_area = img
    else:
        sample_area = img

    pixels = sample_area.reshape(-1, 3)
    current_mids = np.percentile(pixels, 50.0, axis=0)

    # 2. 计算理想 Gamma 组
    gammas = calculate_auto_alignment_gamma(
        current_mids, user_ev_bias, mode=mode,
        strength=strength, skin_protection=skin_protection,
    )

    # 3. 分通道执行变换
    for i in range(3):
        channel = img[:, :, i]

        # 计算 Gamma 变换后的结果
        aligned_channel = np.power(np.clip(channel, 0, 1.0), 1.0 / gammas[i])

        if protect_latitude:
            # --- 宽容度保护逻辑 ---
            # 创建一个平滑的权重掩码 (Weight Mask)
            # 使用 sin^2 函数产生一个在 0.5 处为 1.0，在 0 和 1 处为 0 的平滑曲线
            # 这比简单的线性过渡更能保持影调的连续性
            mask = np.sin(channel * np.pi) ** 2

            # 强化掩码控制：如果你觉得保护力度不够，可以对 mask 做幂运算
            # mask = np.power(mask, 1.2)

            # 混合：原始值与对齐值根据权重混合
            # 极暗和极亮部 (mask->0) 保持原始值，中间调 (mask->1) 完全应用对齐
            img[:, :, i] = channel * (1.0 - mask) + aligned_channel * mask
        else:
            # 无保护模式：全图暴力应用
            img[:, :, i] = aligned_channel

    return np.clip(img, 0, 1.0)
