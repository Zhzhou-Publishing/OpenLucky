import numpy as np


def apply_exposure_3ev(img, ev=0.0):
    """
    适用于 ±3EV，保持高透明度。
    """
    if ev == 0:
        return img.astype(np.float32)

    gain = np.power(2.0, ev)

    if ev > 0:
        # 输入参考压缩：线性感强，仅边缘平滑
        img_exposed = (img * gain) / (1.0 + img * (gain - 1.0) * 0.5)
    else:
        img_exposed = img * gain

    # 强制转回 float32 解决 OpenCV CV_64F 报错
    return np.clip(img_exposed, 0, 1.0).astype(np.float32)


def apply_exposure_5ev(img, ev=0.0):
    """
    适用于 ±5EV，Reinhard 变体色调映射。
    """
    if ev == 0:
        return img.astype(np.float32)

    gain = np.power(2.0, ev)

    if ev > 0:
        # 归一化因子保证 1.0 映射到 1.0
        norm_factor = 1.0 + 0.8
        img_exposed = ((img * gain) / (1.0 + (img * gain) * 0.8)) * norm_factor
    else:
        img_exposed = img * gain

    return np.clip(img_exposed, 0, 1.0).astype(np.float32)


def apply_exposure_7ev(img, ev=0.0):
    """
    适用于 ±7EV，对数压缩映射。
    """
    if ev == 0:
        return img.astype(np.float32)

    gain = np.power(2.0, ev)

    def log_map(x, g):
        eps = 1e-6
        # log1p 极易产生 float64
        return np.log1p(x * g) / np.log1p(g + eps)

    if ev > 0:
        img_exposed = log_map(img, gain)
    else:
        img_exposed = img * gain

    return np.clip(img_exposed, 0, 1.0).astype(np.float32)
