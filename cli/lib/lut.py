"""LUT-based fast paths for registered tone-mapping functions."""

import sys
from pathlib import Path

import numpy as np

from cli.lib.curve.s_curve import power_curve_raw


FUNC_REGISTRY = {"s-curve.power-curve": power_curve_raw}

LUT_NAMESPACE = "com.github.zhzhou-publishing.openlucky"


def _lut_dir():
    # Frozen (PyInstaller bin/openlucky): 'lut/' sits next to the executable.
    # Source/dev: 'lut/' at the repo root — cli/lib/lut.py is three levels in.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "lut"
    return Path(__file__).resolve().parent.parent.parent / "lut"


def _build_param_str(kwargs):
    return "-".join(f"{k}-{f'{v:.2f}'.replace('.', '_')}" for k, v in kwargs.items())


def apply_lut(function_name, image, **kwargs):
    """Apply a registered tone-mapping function to ``image``, preferring a pre-baked LUT.

    Looks up ``<lut_dir>/<namespace>.<function_name>.<param_str>.lut`` (LUT is
    65536-entry uint16, as written by ``openlucky.dev genlut``). If found,
    applies it via numpy indexing in float32 [0, 1]. Otherwise falls back to
    ``FUNC_REGISTRY[function_name](image, **kwargs)``.
    """
    if function_name not in FUNC_REGISTRY:
        raise KeyError(f"Function '{function_name}' is not registered in FUNC_REGISTRY")

    param_str = _build_param_str(kwargs)
    lut_path = _lut_dir() / f"{LUT_NAMESPACE}.{function_name}.{param_str}.lut"

    if lut_path.exists():
        lut = np.fromfile(lut_path, dtype=np.uint16)
        if lut.size == 65536:
            indices = (np.clip(image, 0.0, 1.0) * 65535.0).astype(np.uint16)
            return lut[indices].astype(np.float32) / 65535.0

    return FUNC_REGISTRY[function_name](image, **kwargs)
