import numpy as np


def auto_pk(image, roi=None, strength=1.0, q=5, pivot=None):
    """
    根据图像直方图自动估计 power_curve_raw 的 (p, k)。

    思路：
      p = ROI 内亮度 median（恒等映射到 0.5 处，对扫描黑边/片基底座 robust）。
      k = 在 q% / (100-q)% 两个分位点上分别反解曲线得到 k_hi、k_lo，
          再取对数空间几何平均——单臂拟合会让另一臂飘到 0 或 1，
          双臂兜底两端都不至于塌陷。
      strength<1 时把 k 朝 1.0 软化（k_final = k^strength），给胶片审美留口子。

    容量保险：当 k_hi 和 k_lo 比值超过 10×（高臂物理上不可能达成 —— 典型
    重欠曝/重过曝），降级到 k=1.0；这种图应该靠 pipeline 前面的 EV 校正
    先把动态范围对齐，曲线不该硬扛。

    参数:
    ----------
    image : ndarray
        输入图像，shape (H, W) 或 (H, W, 3)，值域 [0, 1]。
    roi : tuple(x1, y1, x2, y2) or None
        统计区域。None 表示全图。
    strength : float in [0, 1]
        强度软化系数，1.0 走全力，0.0 退化为恒等。
    q : float in (0, 50)
        分位点端点，q=5 用 P5/P95；NLP 风格更激进可用 q=0.5。
    pivot : float in [0.01, 0.99] or None
        如果给定，跳过 median 计算，直接用这个 p 反解 k——
        支持 `--tone 0.4,auto` 这种"固定轴心、自动求对比度"的混合模式。
    """
    if roi is not None:
        x1, y1, x2, y2 = roi
        h, w = image.shape[:2]
        x1 = max(0, min(w, int(round(x1))))
        y1 = max(0, min(h, int(round(y1))))
        x2 = max(0, min(w, int(round(x2))))
        y2 = max(0, min(h, int(round(y2))))
        if x2 - x1 >= 2 and y2 - y1 >= 2:
            sample = image[y1:y2, x1:x2]
        else:
            sample = image
    else:
        sample = image

    if sample.ndim == 3:
        Y = 0.2126 * sample[..., 0] + 0.7152 * sample[..., 1] + 0.0722 * sample[..., 2]
    else:
        Y = sample
    Y = Y.astype(np.float64, copy=False).ravel()

    if pivot is None:
        p_lo, p_mid, p_hi = np.percentile(Y, [q, 50.0, 100.0 - q])
        p = float(np.clip(p_mid, 0.05, 0.95))
    else:
        p_lo, p_hi = np.percentile(Y, [q, 100.0 - q])
        p = float(np.clip(pivot, 0.01, 0.99))

    y_target = 2.0 * (q / 100.0)

    if p_hi > p:
        x_hi = (1.0 - p_hi) / (1.0 - p)
        k_hi = np.log(y_target) / np.log(max(x_hi, 1e-6))
    else:
        k_hi = 1.0
    if p_lo < p:
        x_lo = p_lo / p
        k_lo = np.log(y_target) / np.log(max(x_lo, 1e-6))
    else:
        k_lo = 1.0

    k_hi = max(k_hi, 1e-3)
    k_lo = max(k_lo, 1e-3)

    # 容量保险：两臂目标差太大 → 单条 power curve 表达不出来，降级到恒等
    ratio = max(k_hi, k_lo) / min(k_hi, k_lo)
    if ratio > 10.0:
        k = 1.0
    else:
        k = float(np.exp(0.5 * (np.log(k_hi) + np.log(k_lo))))

    strength = float(np.clip(strength, 0.0, 1.0))
    if strength < 1.0:
        k = float(np.power(k, strength))

    k = float(np.clip(k, 0.4, 2.2))
    return p, k


def power_curve_raw(image, p=0.5, k=1.0):
    """
    底层 Power Curve 实现，直接暴露数学参数。

    参数:
    ----------
    image : ndarray
        输入图像 (建议范围 0.0-1.0)。
    p : float (Pivot)
        中点位置（轴心）。控制曲线转折的阈值。
        - p=0.5: 对称 S 曲线。
        - p<0.5: 轴心左移，暗部压缩更剧烈。
        - p>0.5: 轴心右移，高光压缩更剧烈。
    k : float (Exponent)
        幂指数（对比度）。
        - k=1.0: 线性映射（无变化）。
        - k>1.0: 增加对比度（标准 S 型）。
        - k<1.0: 降低对比度（反 S 型）。
    """
    # 避免除以 0 的极端情况
    p = np.clip(p, 0.01, 0.99)

    # 分段幂运算实现
    # 通过将 image/p 和 (1-image)/(1-p) 归一化到 [0, 1] 空间再进行幂运算
    res = np.where(
        image < p,
        0.5 * np.power(image / p, k),
        1.0 - 0.5 * np.power((1.0 - image) / (1.0 - p), k),
    )

    return np.clip(res, 0.0, 1.0)
