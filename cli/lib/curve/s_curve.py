import numpy as np


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
