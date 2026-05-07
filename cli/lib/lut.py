"""LUT-based fast paths for registered tone-mapping functions."""

import sys
from pathlib import Path

import numpy as np

from cli.lib.curve.s_curve import power_curve_raw
from cli.lib.curve.gamma import apply_gamma
from cli.lib.exposure import (
    apply_exposure_3ev,
    apply_exposure_5ev,
    apply_exposure_7ev,
)


FUNC_REGISTRY = {
    "s-curve.power-curve": power_curve_raw,
    "common.apply-exposure-3ev": apply_exposure_3ev,
    "common.apply-exposure-5ev": apply_exposure_5ev,
    "common.apply-exposure-7ev": apply_exposure_7ev,
    "common.gamma": apply_gamma,
}

LUT_NAMESPACE = "com.github.zhzhou-publishing.openlucky"


def _lut_dir():
    # Frozen (PyInstaller bin/openlucky): 'lut/' sits next to the executable.
    # Source/dev: 'lut/' at the repo root — cli/lib/lut.py is three levels in.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "lut"
    return Path(__file__).resolve().parent.parent.parent / "lut"


def _format_value(v):
    # Negative sign becomes literal 'n' so file names stay shell-safe and
    # never look like an argparse flag.
    if v < 0:
        return f"n{(-v):.2f}".replace(".", "_")
    return f"{v:.2f}".replace(".", "_")


def _build_param_str(kwargs):
    return "-".join(f"{k}-{_format_value(v)}" for k, v in kwargs.items())


def lut_path_for(lut_dir, function_name, kwargs):
    """Resolve the on-disk path for a given (function_name, kwargs).

    Layout: each dot in ``<namespace>.<function_name>.<param_str>`` becomes a
    directory boundary. The trailing segment is the ``.lut`` file. Example::

        common.apply-exposure-7ev with ev=-7.0 ->
          lut/com/github/zhzhou-publishing/openlucky/common/apply-exposure-7ev/ev-n7_00.lut
    """
    param_str = _build_param_str(kwargs)
    full_id = f"{LUT_NAMESPACE}.{function_name}.{param_str}"
    parts = full_id.split(".")
    return Path(lut_dir).joinpath(*parts[:-1], f"{parts[-1]}.lut")


def apply_lut(function_name, image, **kwargs):
    """Apply a registered tone-mapping function to ``image``, preferring a pre-baked LUT.

    Looks up the hierarchical LUT path; if the file exists and has 65536
    uint16 entries, applies it via numpy indexing in float32 [0, 1].
    Otherwise falls back to ``FUNC_REGISTRY[function_name](image, **kwargs)``.
    """
    if function_name not in FUNC_REGISTRY:
        raise KeyError(f"Function '{function_name}' is not registered in FUNC_REGISTRY")

    lut_path = lut_path_for(_lut_dir(), function_name, kwargs)

    if lut_path.exists():
        lut = np.fromfile(lut_path, dtype=np.uint16)
        if lut.size == 65536:
            indices = (np.clip(image, 0.0, 1.0) * 65535.0).astype(np.uint16)
            return lut[indices].astype(np.float32) / 65535.0

    return FUNC_REGISTRY[function_name](image, **kwargs)
