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


def auto_latitude_curve(image, pivot, roi=None, contrast=1.0, strength=1.0,
                        budget_hi=1.5, budget_lo=1.0, k_min=0.45, k_max=1.0,
                        steps=12, max_samples=200000):
    """自动求"宽容度矫正"的曝光反差 k（保住高光阴影）。

    与 auto_pk 不同：auto_pk 以"把对比拉到目标"为目标，对已经偏软的负片扫描
    常给出 k>1（增对比），把高光打爆。这里只在保宽容度的区间 k<=1.0 取值，并
    选"在裁切预算内最大的 k"——即用最自然的对比，前提是预测的**最终**裁切
    （经过下游 auto-levels 拉伸与 contrast 之后）不超预算。需要压缩才压缩：会
    裁切的图给更强的反 S，不会裁切的图保持 k≈1.0。

    参数:
    ----------
    image : ndarray  (H, W, 3)，值域 [0,1]，stage-7 tone 之前的状态。
    pivot : float     曲线轴心 p（用 auto_pk 求出的中位数）。
    roi   : (x1,y1,x2,y2) or None  统计区域，None 为全图。
    contrast : float  下游 auto-levels 的对比系数，用于准确预测最终裁切。
    strength : float in [0,1]  软化系数，1.0 全力，0.0 退化为 k=1.0（不矫正）。
    budget_hi / budget_lo : float  高光 / 阴影裁切像素占比预算（%）。
    k_min / k_max : float  k 取值范围；上限 1.0 保证永不反向增对比。
    """
    if roi is not None:
        x1, y1, x2, y2 = roi
        h, w = image.shape[:2]
        x1 = max(0, min(w, int(round(x1)))); x2 = max(0, min(w, int(round(x2))))
        y1 = max(0, min(h, int(round(y1)))); y2 = max(0, min(h, int(round(y2))))
        sample = image[y1:y2, x1:x2] if (x2 - x1 >= 2 and y2 - y1 >= 2) else image
    else:
        sample = image

    flat = sample.reshape(-1, sample.shape[-1]).astype(np.float64, copy=False)
    # 等距抽样而非 INTER_AREA 缩放：均值缩放会抹平极端像素、低估裁切；等距抽样
    # 保持数值分布，裁切占比无偏。
    if flat.shape[0] > max_samples:
        flat = flat[:: flat.shape[0] // max_samples]
    p = float(np.clip(pivot, 0.01, 0.99))

    def clip_pct(k):
        toned = power_curve_raw(flat, p, k)
        hi = lo = 0.0
        for c in range(toned.shape[-1]):
            ch = toned[:, c]
            c_lo = np.percentile(ch, 0.01)
            c_hi = np.percentile(ch, 99.99)
            st = np.clip((ch - c_lo) / max(c_hi - c_lo, 1e-5) * contrast, 0.0, 1.0)
            hi = max(hi, float(np.mean(st > 253.0 / 255.0) * 100.0))
            lo = max(lo, float(np.mean(st < 2.0 / 255.0) * 100.0))
        return lo, hi

    best = k_min
    for k in np.linspace(k_max, k_min, steps):  # 最大 k 优先 → 取最自然对比
        lo, hi = clip_pct(float(k))
        if hi <= budget_hi and lo <= budget_lo:
            best = float(k)
            break

    strength = float(np.clip(strength, 0.0, 1.0))
    return float(1.0 - strength * (1.0 - best))  # strength<1 软化回 k=1.0


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
