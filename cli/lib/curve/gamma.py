import numpy as np


def apply_gamma(image, gamma=1.0):
    """Per-pixel gamma correction: ``image ** gamma``, returned as float32.

    Mirrors the inline ``np.power(img, preset_gamma)`` previously used in
    ``process_film``. Caller is responsible for ensuring image is in [0, 1].
    """
    return np.power(image, gamma).astype(np.float32)
