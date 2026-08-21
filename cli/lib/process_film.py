import io
import math
import rawpy
import numpy as np
import cv2

from cli.constants.image_formats import RAW_EXTENSIONS
from cli.lib.lut import apply_lut
from cli.lib.curve.s_curve import auto_pk, auto_latitude_curve, power_curve_raw
from cli.lib.process_film_functions.gamma_alignment import apply_gamma_alignment
from cli.lib.process_film_functions.density import (
    apply_post_gamma_adjustments,
    auto_base_mask,
    decrosstalk,
    estimate_density_limits,
    mask_to_density,
    normalize_density,
    subtract_mask,
    to_density,
)
from cli.lib.dust import remove_defects

# ── 色彩校正模式 ──────────────────────────────────────────────────────────
# 每个模式定义 gamma 对齐强度、肤色保护开关、tone 映射强度。
# 整个链路只传递 color_mode 字符串，内部参数不暴露给前端。
COLOR_MODES = {
    "skin_protect": {"gamma_strength": 0.3, "skin_protection": True,  "tone_strength": 0.6},
    "balanced":     {"gamma_strength": 0.6, "skin_protection": True,  "tone_strength": 1.0},
    "deep":         {"gamma_strength": 1.0, "skin_protection": False, "tone_strength": 1.0},
    "preserve":     {"gamma_strength": 0.1, "skin_protection": True,  "tone_strength": 0.2},
}


def resolve_wp_roi_to_actual(roi, basis_wh, rotate_clockwise, actual_wh):
    """Map a basis-frame ROI back to the actual decoded image's coords.

    The UI captures the ROI on a working-dir preview that is resized AND
    already rotated. CLI reads the un-rotated original at full resolution,
    so the ROI must be (a) un-rotated within the basis frame, then
    (b) scaled to the actual image dims, before sampling.

    roi: (x1, y1, x2, y2) in the basis frame.
    basis_wh: (Wb, Hb) of the basis frame (post-rotation dims).
    rotate_clockwise: 0/90/180/270, the rotation that produced the basis frame.
    actual_wh: (W_actual, H_actual) of the un-rotated decoded image.

    Returns an integer (x1, y1, x2, y2) clipped to actual image bounds and
    guaranteed to satisfy x2>x1, y2>y1.
    """
    Wb, Hb = basis_wh
    x1, y1, x2, y2 = roi

    # Step 1: un-rotate inside the basis frame. Closed-form per angle.
    if rotate_clockwise == 0:
        Wu, Hu = Wb, Hb
        ux1, uy1, ux2, uy2 = x1, y1, x2, y2
    elif rotate_clockwise == 90:
        Wu, Hu = Hb, Wb
        ux1, uy1, ux2, uy2 = y1, Wb - x2, y2, Wb - x1
    elif rotate_clockwise == 180:
        Wu, Hu = Wb, Hb
        ux1, uy1, ux2, uy2 = Wb - x2, Hb - y2, Wb - x1, Hb - y1
    elif rotate_clockwise == 270:
        Wu, Hu = Hb, Wb
        ux1, uy1, ux2, uy2 = Hb - y2, x1, Hb - y1, x2
    else:
        raise ValueError(f"Unsupported rotate_clockwise: {rotate_clockwise}")

    # Step 2: scale to actual image dims. floor on top-left, ceil on
    # bottom-right so a thin slice doesn't collapse to an empty rect.
    Wa, Ha = actual_wh
    sx = Wa / Wu
    sy = Ha / Hu
    fx1 = math.floor(ux1 * sx)
    fy1 = math.floor(uy1 * sy)
    fx2 = math.ceil(ux2 * sx)
    fy2 = math.ceil(uy2 * sy)

    # Step 3: clip + degenerate guard. parse_area in the CLI rejects
    # x2<=x1 / y2<=y1 up-front, but after scaling we can still wind up
    # with a 0-pixel rect on tiny basis frames; nudge to ensure validity.
    fx1 = max(0, min(Wa - 1, fx1))
    fy1 = max(0, min(Ha - 1, fy1))
    fx2 = max(fx1 + 1, min(Wa, fx2))
    fy2 = max(fy1 + 1, min(Ha, fy2))
    return fx1, fy1, fx2, fy2


def get_white_point_manual(img, roi=None, percentile=99.0):
    """
    手动 ROI 采样：在原图中绘制红框，并强制物理切片以确保采样准确。
    """
    # 确保图像是 float32 格式且是副本，防止修改原始输入
    img_work = img.astype(np.float32).copy()
    h, w = img_work.shape[:2]

    if roi is not None:
        # 解析坐标并强制转为整数
        x1, y1, x2, y2 = [int(round(c or 0)) for c in roi]

        # 边界安全检查
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        # 【核心操作】物理切片：只把框内的数据拿出来给计算模块
        target_area = img_work[y1:y2, x1:x2].copy()

        # 如果切片失败（比如坐标写反了），回退到全图
        if target_area.size == 0:
            print("Warning: Invalid ROI size. Using full image.")
            target_area = img_work
    else:
        target_area = img_work

    # 1. 计算白点 (严格在 target_area 内采样)
    pixels = target_area.reshape(-1, 3)
    r_w = np.percentile(pixels[:, 0], percentile)
    g_w = np.percentile(pixels[:, 1], percentile)
    b_w = np.percentile(pixels[:, 2], percentile)
    wp = np.array([r_w, g_w, b_w])

    return wp


def process_film_bytestream_with_params(
    input_bytes,
    preset_mask_r,
    preset_mask_g,
    preset_mask_b,
    preset_gamma=1.0,
    preset_contrast=1.0,
    preset_contrast_r=1.0,
    preset_contrast_g=1.0,
    preset_contrast_b=1.0,
    rotate_clockwise=0,
    wp_roi_x1=None,
    wp_roi_y1=None,
    wp_roi_x2=None,
    wp_roi_y2=None,
    area_basis_w=None,
    area_basis_h=None,
    white_balance="auto",
    exposure_ev_mode="3ev",
    exposure_ev=0.0,
    tone_pivot=0.5,
    tone_curve=0.5,
    is_raw=False,
    color_mode="skin_protect",
    dust=None,
    dust_rois=None,
    algo="v1",
    saturation=1.0,
):
    """
    Process byte stream image, supports RAW format toggle

    dust:     (grain_level, dust_size) or None — presence enables dust removal.
    dust_rois: list of (x1, y1, x2, y2) rects (basis frame when area_basis given,
              otherwise actual-image pixels). pr/024.dust.md
    algo:     "v1" (default, legacy linear-domain) or "v2" (density-domain,
              see design/film-color-v2.md). v1 behaviour is byte-identical.
    saturation: multiplier (1.0 = neutral); used by v2 post-gamma colour.
    """
    # v2 engine: density-domain inversion. See design/film-color-v2.md.
    if algo == "v2":
        return _process_film_v2_bytestream(
            input_bytes,
            is_raw=is_raw,
            mask_r=preset_mask_r,
            mask_g=preset_mask_g,
            mask_b=preset_mask_b,
            preset_gamma=preset_gamma,
            preset_contrast=preset_contrast,
            preset_contrast_r=preset_contrast_r,
            preset_contrast_g=preset_contrast_g,
            preset_contrast_b=preset_contrast_b,
            rotate_clockwise=rotate_clockwise,
            wp_roi_x1=wp_roi_x1,
            wp_roi_y1=wp_roi_y1,
            wp_roi_x2=wp_roi_x2,
            wp_roi_y2=wp_roi_y2,
            area_basis_w=area_basis_w,
            area_basis_h=area_basis_h,
            white_balance=white_balance,
            exposure_ev=exposure_ev,
            tone_pivot=tone_pivot,
            tone_curve=tone_curve,
            color_mode=color_mode,
            saturation=saturation,
            dust=dust,
            dust_rois=dust_rois,
        )

    # 1. Explicitly decode image
    if is_raw:
        # Process RAW format: use rawpy engine
        with rawpy.imread(io.BytesIO(input_bytes)) as raw:
            # Determine demosaic algorithm based on camera format
            # Since we don't have filename info in byte stream mode, we need to detect format
            # For simplicity, default to AAHD unless Fuji RAF is detected via metadata
            # Note: Accurate Fuji RAF detection from byte stream would require additional metadata parsing
            # Using AAHD as default for byte stream processing
            demosaic_algorithm = rawpy.DemosaicAlgorithm.AAHD

            # postprocess returns uint16 array in RGB order
            img = (
                raw.postprocess(
                    # Demosaic algorithm (default AAHD for byte stream processing)
                    demosaic_algorithm=demosaic_algorithm,
                    # 2. Crucial: Disable LibRaw's built-in noise reduction
                    # AAHD may produce minor artifacts, LibRaw might use FBDD to remove them by default,
                    # but FBDD damages film grain texture. To preserve authentic RAW, it must be turned off.
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                    # 3. Gamma: Must remain (1, 1) linear.
                    gamma=(1, 1),
                    # 4. Brightness: Must be True. Disable automatic brightness stretching.
                    no_auto_bright=True,
                    # 5. Bit depth: Must be 16. For dynamic range after negative inversion.
                    output_bps=16,
                    # 6. White balance:
                    # For photographing negatives, it's recommended to enable camera WB
                    # (calibrated against the backlight panel during shooting),
                    # so the resulting TIFF channel ratios are roughly correct, facilitating subsequent inversion.
                    use_camera_wb=True,
                    # 7. Brightness gain: Keep at 1.0.
                    bright=1.0,
                ).astype(np.float32)
                / 65535.0
            )
        is_16bit_target = True
    else:
        # Process regular formats: use OpenCV engine
        nparr = np.frombuffer(input_bytes, np.uint8)
        img_raw = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            return None

        # Convert to RGB (OpenCV default is BGR)
        img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB).astype(np.float32)

        max_val = 65535.0 if img_raw.dtype == np.uint16 else 255.0
        img /= max_val
        is_16bit_target = img_raw.dtype == np.uint16

    # If a basis frame is supplied, the ROI is in that frame's (post-rotation,
    # post-resize) coords; remap to the actual decoded image's un-rotated
    # frame before sampling. Without basis we fall back to interpreting the
    # ROI as already in actual coords (legacy CLI behavior).
    roi_complete = (
        wp_roi_x1 is not None
        and wp_roi_y1 is not None
        and wp_roi_x2 is not None
        and wp_roi_y2 is not None
    )
    if roi_complete and area_basis_w and area_basis_h:
        h_actual, w_actual = img.shape[:2]
        wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2 = resolve_wp_roi_to_actual(
            (wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2),
            (int(area_basis_w), int(area_basis_h)),
            rotate_clockwise,
            (w_actual, h_actual),
        )

    # 2. Remove color mask (operate in 0-1 space)
    # At this point, img is confirmed to be in RGB order

    # --- 增加基于缩放采样的溢出控制迭代逻辑 ---
    # 使用下采样图像进行快速迭代尋优。**溢出统计只在 WP ROI 内部进行**：
    # 否则底座/扫描边/片基外缘等非影像区域会贡献大量溢出像素，把循环
    # 骗成提前达标而停止，让影像内部的真实溢出得不到充分压制。
    h, w = img.shape[:2]
    scale = 0.125  # 1/8 采样
    img_small = cv2.resize(
        img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
    )

    # 把 WP ROI 映射到下采样坐标系；ROI 不可用时回退到整张小图
    sh, sw = img_small.shape[:2]
    if roi_complete:
        rx1 = max(0, min(sw, int(round(wp_roi_x1 * scale))))
        ry1 = max(0, min(sh, int(round(wp_roi_y1 * scale))))
        rx2 = max(0, min(sw, int(round(wp_roi_x2 * scale))))
        ry2 = max(0, min(sh, int(round(wp_roi_y2 * scale))))
        if rx2 - rx1 < 2 or ry2 - ry1 < 2:
            roi_small = img_small
        else:
            roi_small = img_small[ry1:ry2, rx1:rx2]
    else:
        roi_small = img_small

    current_mask_r = float(preset_mask_r)
    current_mask_g = float(preset_mask_g)
    current_mask_b = float(preset_mask_b)

    max_iter = 15
    for i in range(max_iter):
        # 在 ROI 小图上计算溢出面积
        test_r = roi_small[:, :, 0] / (current_mask_r / 255.0)
        test_g = roi_small[:, :, 1] / (current_mask_g / 255.0)
        test_b = roi_small[:, :, 2] / (current_mask_b / 255.0)

        # 统计 ROI 内部溢出率 (高于 1.0 的通道值占比)
        overflow_count = (
            (test_r > 1.0).sum() + (test_g > 1.0).sum() + (test_b > 1.0).sum()
        )
        overflow_ratio = overflow_count / max(roi_small.size, 1)

        # 如果溢出率在 5% 以内，或者达到迭代上限，跳出
        if overflow_ratio <= 0.05 or i == max_iter - 1:
            break

        # 否则，增加色罩值以降低增益（按 5% 步进）
        current_mask_r *= 1.05
        current_mask_g *= 1.05
        current_mask_b *= 1.05

    # 应用最终确定的 Mask 值到大图
    img[:, :, 0] /= current_mask_r / 255.0  # Red
    img[:, :, 1] /= current_mask_g / 255.0  # Green
    img[:, :, 2] /= current_mask_b / 255.0  # Blue

    # 3. Color inversion (in 0-1 space, it's 1.0 - img)
    img = 1.0 - img

    # --- 3.0 算法除尘（手动 ROI，见 pr/024.dust.md）---
    # 灰尘在负片上是近黑点，反转后成中性亮斑。放在反转后、白点采样前，
    # 避免灰尘把 WP ROI 的白点/色阶顶偏。ROI 与 --area 同坐标系：--area-basis
    # 存在时按 basis 帧映射到实际解码图，否则按实际像素解释。
    if dust is not None and dust_rois:
        h_img, w_img = img.shape[:2]
        grain_level, dust_size = dust
        regions = []
        for rx in dust_rois:
            if area_basis_w and area_basis_h:
                mx1, my1, mx2, my2 = resolve_wp_roi_to_actual(
                    rx,
                    (int(area_basis_w), int(area_basis_h)),
                    rotate_clockwise,
                    (w_img, h_img),
                )
            else:
                mx1, my1, mx2, my2 = rx
            regions.append(
                {"shape": "rect", "x1": mx1, "y1": my1, "x2": mx2, "y2": my2}
            )
        img = remove_defects(
            img, regions, {"grain_level": grain_level, "dust_size": dust_size}
        )

    # --- 3.1 采样白点 ---
    # white_point_vec: [r_w, g_w, b_w]
    white_point_vec = get_white_point_manual(
        img, roi=[wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2], percentile=99.0
    )

    # --- 3.2 白平衡与偏移逻辑 ---
    # 默认：no 白平衡 (仅拉满曝光，不改变比例)
    scaling_factor = np.max(white_point_vec)
    gains = np.array([1.0 / scaling_factor] * 3)

    if white_balance != "none":
        # 首先执行自动白平衡 (AWB) 的基础增益
        # 让 RGB 比例强制回归 1:1:1
        awb_gains = 1.0 / (white_point_vec + 1e-6)

        if white_balance == "auto":
            gains = awb_gains
        elif isinstance(white_balance, (list, tuple)):
            # 处理 x, y 偏移逻辑
            off_x, off_y = white_balance  # 输入范围 [-50, 50]

            # 将 50 映射为 0.5 (即 50% 的增益偏移)
            shift_x = off_x / 100.0
            shift_y = off_y / 100.0

            # 应用偏移
            gains[0] = awb_gains[0] * (1.0 + shift_x)  # 红
            gains[2] = awb_gains[2] * (1.0 - shift_x)  # 蓝
            gains[1] = awb_gains[1] * (1.0 - shift_y)  # 绿

    # --- 3.3 再次归一化 (防溢出) ---
    # 无论怎么调，确保最亮的那个通道在应用增益后刚好是 1.0
    # 这样可以维持曝光稳定，只改色调
    max_after_wb = np.max(white_point_vec * gains)
    gains /= max_after_wb + 1e-6

    # 应用增益
    img *= gains
    img = np.clip(img, 0, 1.0)

    # --- 中间调对齐 ---
    # 逐通道 gamma 校正，以绿色通道中位数为基准对齐 RGB 中间调。
    # protect_latitude=True 通过 sin² 权重将校正限制在中间调，保留高光与阴影。
    # user_ev_bias 仅在 mode='ev_target' 时生效。
    # strength / skin_protection 由 color_mode 决定。
    mode_cfg = COLOR_MODES.get(color_mode, COLOR_MODES["skin_protect"])
    img = apply_gamma_alignment(
        img,
        roi=(wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2),
        user_ev_bias=0.0,  # 拍摄意图需要另外传入参数！！！
        protect_latitude=True,
        strength=mode_cfg["gamma_strength"],
        skin_protection=mode_cfg["skin_protection"],
    )

    # 4. Gamma correction：同样走 LUT 通道。gamma=1.0 时跳过避免量化损失。
    # For linear RAW, input around 0.45 is recommended; for gamma-corrected images, around 1.0 for fine-tuning
    if preset_gamma != 1.0:
        img = apply_lut("common.gamma", img, gamma=preset_gamma)

    # 4.5 Tone mapping：分段幂曲线，把动态范围压进显示空间。
    # 单一 gamma 无法同时"提阴影 + 压高光"——它是单调函数；分段幂曲线（k<1
    # 时是反 S 形）以 p 为轴心，下半段提亮、上半段压暗，正好解决"衣服/树叶
    # 看得见但天空过曝"或反之的二选一困境。
    # p=0.5/k=0.5 是常见胶片冲扫起点；k<1 反 S（提阴影压高光），k>1 标准 S
    # （增对比），k=1 恒等。power_curve_raw 内部 np.power(float32, python_float)
    # 可能升到 float64，否则后面 cv2.cvtColor 会因 CV_64F 报错。
    # auto 模式：tone_pivot 和 tone_curve 各自独立可以是 float 或 'auto'/'auto:STR'。
    # 轴心 p 由 auto_pk 取中位数；曝光反差 k 走"宽容度自动"——以保住高光阴影
    # 为目标（在裁切预算内取最自然的对比），不是 auto_pk 的"增对比到目标"逻辑，
    # 后者对偏软的负片会给 k>1 打爆高光，正是用户每次手动拉到 -100 的原因。
    pivot_is_auto = (tone_pivot == 'auto')
    curve_is_auto = isinstance(tone_curve, str) and tone_curve.startswith('auto')
    if pivot_is_auto or curve_is_auto:
        strength = mode_cfg["tone_strength"]
        if isinstance(tone_curve, str) and tone_curve.startswith('auto:'):
            strength = float(tone_curve.split(':', 1)[1])
        roi = (
            (wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2)
            if roi_complete
            else None
        )
        # 手动 pivot 时传给 auto_pk 让其与之自洽；auto 时取 ROI 中位数。
        pivot_override = None if pivot_is_auto else float(tone_pivot)
        auto_p, _ = auto_pk(img, roi=roi, strength=strength, pivot=pivot_override)
        eff_pivot = auto_p  # = pivot_override when manual
        if curve_is_auto:
            # contrast=preset_contrast：让宽容度算法预测下游 auto-levels 的实际裁切。
            eff_curve = auto_latitude_curve(
                img, eff_pivot, roi=roi,
                contrast=preset_contrast, strength=strength,
            )
        else:
            eff_curve = float(tone_curve)
    else:
        eff_pivot, eff_curve = tone_pivot, tone_curve
    img = power_curve_raw(img, p=eff_pivot, k=eff_curve).astype(np.float32)

    # 5. Auto levels and contrast fine-tuning
    # Store per-channel contrast settings in a list for iteration
    channel_contrasts = [preset_contrast_r, preset_contrast_g, preset_contrast_b]

    # **分位数只在 WP ROI 内统计**：否则底座/扫描边那些被压成 0 的非影像像素
    # 会霸占 0.01% 分位点，让 low 永远等于 0，阴影抬不起来，褶皱细节湮没。
    # 拉伸变换仍然作用于全图，保证管线行为一致。
    h_full, w_full = img.shape[:2]
    if roi_complete:
        lx1 = max(0, min(w_full, int(round(wp_roi_x1))))
        ly1 = max(0, min(h_full, int(round(wp_roi_y1))))
        lx2 = max(0, min(w_full, int(round(wp_roi_x2))))
        ly2 = max(0, min(h_full, int(round(wp_roi_y2))))
        if lx2 - lx1 < 2 or ly2 - ly1 < 2:
            levels_sample = img
        else:
            levels_sample = img[ly1:ly2, lx1:lx2]
    else:
        levels_sample = img

    for i in range(3):
        # 注意：由于我们在 Step 2 允许了 5% 溢出，这里的 low 采样应保持保守（0.01%）以防细节丢失
        low = np.percentile(levels_sample[:, :, i], 0.01)
        high = np.percentile(levels_sample[:, :, i], 99.99)
        # Apply combined contrast: global * channel_specific
        combined_contrast = preset_contrast * channel_contrasts[i]
        # 增加一个极其微小的分母保护，防止 high - low 过窄导致的数值暴增
        denominator = max(high - low, 1e-5)
        # Linear stretch and apply contrast
        img[:, :, i] = np.clip(
            (img[:, :, i] - low) * (1.0 / denominator) * combined_contrast,
            0,
            1.0,
        )

    # 5.5 曝光调整（最终亮度增益）：必须放在自动色阶之后。自动色阶按通道做
    # min-max 拉伸，是尺度不变变换，会把曝光的纯增益精确约掉；放在它之后，曝光
    # 才能作为可预测的最终亮度控制生效。走 LUT 通道，未命中时回退到原始函数；
    # LUT 与回退函数均把输出钳在 [0,1]，编码安全。ev=0 时跳过避免量化损失。
    if exposure_ev != 0.0:
        img = apply_lut(
            f"common.apply-exposure-{exposure_ev_mode}",
            img,
            ev=exposure_ev,
        )

    # 6. Rotate image if needed (before encoding)
    if rotate_clockwise != 0:
        # Rotate clockwise by the specified degrees
        # OpenCV's rotate function only supports 90 degree multiples
        if rotate_clockwise == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rotate_clockwise == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif rotate_clockwise == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # 7. Encode back to byte stream
    # Remember to convert back to BGR for OpenCV encoding
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    if is_16bit_target:
        # Output 16bit TIFF to preserve details
        success, encoded_img = cv2.imencode(
            ".tif", (img_bgr * 65535.0).astype(np.uint16)
        )
    else:
        # Output 8bit PNG
        success, encoded_img = cv2.imencode(".png", (img_bgr * 255.0).astype(np.uint8))

    return encoded_img.tobytes() if success else None


def _process_film_v2_bytestream(
    input_bytes,
    is_raw=False,
    mask_r=0.0,
    mask_g=0.0,
    mask_b=0.0,
    preset_gamma=1.0,
    preset_contrast=1.0,
    preset_contrast_r=1.0,
    preset_contrast_g=1.0,
    preset_contrast_b=1.0,
    rotate_clockwise=0,
    wp_roi_x1=None,
    wp_roi_y1=None,
    wp_roi_x2=None,
    wp_roi_y2=None,
    area_basis_w=None,
    area_basis_h=None,
    white_balance="auto",
    exposure_ev=0.0,
    tone_pivot=0.5,
    tone_curve=0.5,
    color_mode="skin_protect",
    saturation=1.0,
    dust=None,
    dust_rois=None,
):
    """v2 engine: density-domain inversion.

    See design/film-color-v2.md. Key differences from v1:
      - works in optical density (-log10(T)) where the mask is *subtracted*,
        not divided (additive in log domain);
      - Status M decross-talk matrix (default on);
      - per-channel D-min/D-max normalization, which both inverts the negative
        and restores each channel's dynamic range;
      - manual white-balance (x, y) applied as post-gamma temperature/tint,
        AFTER normalization and mid-tone alignment (fixes the v1 direction bug);
      - per-channel contrast applied as density endpoint offsets (decision 1);
      - exposure as an additive density shift before normalization.
    """
    # ── decode (identical input assumptions to v1) ──────────────────────────
    if is_raw:
        with rawpy.imread(io.BytesIO(input_bytes)) as raw:
            img = (
                raw.postprocess(
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AAHD,
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                    gamma=(1, 1),
                    no_auto_bright=True,
                    output_bps=16,
                    use_camera_wb=True,
                    bright=1.0,
                ).astype(np.float32)
                / 65535.0
            )
        is_16bit_target = True
    else:
        nparr = np.frombuffer(input_bytes, np.uint8)
        img_raw = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            return None
        img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB).astype(np.float32)
        max_val = 65535.0 if img_raw.dtype == np.uint16 else 255.0
        img /= max_val
        is_16bit_target = img_raw.dtype == np.uint16

    # ── ROI remap (basis frame -> actual frame), same as v1 ─────────────────
    roi_complete = (
        wp_roi_x1 is not None
        and wp_roi_y1 is not None
        and wp_roi_x2 is not None
        and wp_roi_y2 is not None
    )
    if roi_complete and area_basis_w and area_basis_h:
        h_actual, w_actual = img.shape[:2]
        wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2 = resolve_wp_roi_to_actual(
            (wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2),
            (int(area_basis_w), int(area_basis_h)),
            rotate_clockwise,
            (w_actual, h_actual),
        )
    roi = (wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2) if roi_complete else None

    # ── mask: eyedropper value preferred; auto 99-percentile as fallback ────
    mask = np.array([mask_r, mask_g, mask_b], dtype=np.float32)
    if not np.isfinite(mask).all() or mask.min() <= 0.0:
        mask = np.clip(auto_base_mask(img), 1.0, 255.0)
    mask_density = mask_to_density(mask)

    # ── density domain: subtract mask, then decross-talk ────────────────────
    d = to_density(img)
    d_net = subtract_mask(d, mask_density[None, None, :])
    d_true = decrosstalk(d_net)  # Status M, default on

    # Endpoints estimated from clean density so exposure below does not
    # rescale them (limits are computed independently of the render).
    d_min, d_max = estimate_density_limits(d_true, roi=roi)

    # Decision 1: per-channel contrast becomes density endpoint offsets.
    # contrast > 1 narrows the range around its midpoint (steeper = more
    # contrast); contrast < 1 widens it. Each channel scales the global value.
    channel_contrasts = [
        preset_contrast * preset_contrast_r,
        preset_contrast * preset_contrast_g,
        preset_contrast * preset_contrast_b,
    ]
    for i in range(3):
        mid = (d_min[i] + d_max[i]) / 2.0
        half = (d_max[i] - d_min[i]) / 2.0 / max(channel_contrasts[i], 1e-3)
        d_min[i] = mid - half
        d_max[i] = mid + half

    # Exposure as an additive density shift before normalization: +1 EV lifts
    # density by log10(2), brightening the positive against the fixed limits.
    if exposure_ev != 0.0:
        d_true = d_true + exposure_ev * math.log10(2.0)

    # Normalization both inverts the negative and restores dynamic range.
    img = np.clip(normalize_density(d_true, d_min, d_max), 0.0, 1.0)

    # ── dust removal (after inversion, before downstream sampling) ──────────
    if dust is not None and dust_rois:
        h_img, w_img = img.shape[:2]
        grain_level, dust_size = dust
        regions = []
        for rx in dust_rois:
            if area_basis_w and area_basis_h:
                mx1, my1, mx2, my2 = resolve_wp_roi_to_actual(
                    rx,
                    (int(area_basis_w), int(area_basis_h)),
                    rotate_clockwise,
                    (w_img, h_img),
                )
            else:
                mx1, my1, mx2, my2 = rx
            regions.append({"shape": "rect", "x1": mx1, "y1": my1, "x2": mx2, "y2": my2})
        img = remove_defects(
            img, regions, {"grain_level": grain_level, "dust_size": dust_size}
        )

    # ── gamma, then mid-tone alignment (decision 2: after normalization) ────
    if preset_gamma != 1.0:
        img = np.power(img, 1.0 / preset_gamma)
    mode_cfg = COLOR_MODES.get(color_mode, COLOR_MODES["skin_protect"])
    img = apply_gamma_alignment(
        img,
        roi=roi,
        user_ev_bias=0.0,  # shooting intent is not plumbed here (same as v1)
        protect_latitude=True,
        strength=mode_cfg["gamma_strength"],
        skin_protection=mode_cfg["skin_protection"],
    )

    # ── post-gamma colour: manual WB (x, y) -> temperature/tint ─────────────
    temperature, tint = 0.0, 0.0
    if isinstance(white_balance, (list, tuple)) and len(white_balance) == 2:
        temperature = float(white_balance[0]) / 50.0  # x: -50..50 -> -1..1
        tint = float(white_balance[1]) / 50.0          # y: -50..50 -> -1..1
    # "auto"/"none" get no explicit shift: per-channel normalization plus the
    # mid-tone alignment above already serve auto white balance.
    img = apply_post_gamma_adjustments(
        img,
        saturation=max(-1.0, min(1.0, saturation - 1.0)),
        temperature=temperature,
        tint=tint,
    )

    # ── tone mapping (latitude curve), same semantics as v1 ─────────────────
    pivot_is_auto = tone_pivot == "auto"
    curve_is_auto = isinstance(tone_curve, str) and tone_curve.startswith("auto")
    if pivot_is_auto or curve_is_auto:
        strength = mode_cfg["tone_strength"]
        if isinstance(tone_curve, str) and tone_curve.startswith("auto:"):
            strength = float(tone_curve.split(":", 1)[1])
        pivot_override = None if pivot_is_auto else float(tone_pivot)
        auto_p, _ = auto_pk(img, roi=roi, strength=strength, pivot=pivot_override)
        eff_pivot = auto_p
        if curve_is_auto:
            # v2 has no downstream linear auto-levels, so the latitude
            # predictor is told the stretch is neutral.
            eff_curve = auto_latitude_curve(
                img, eff_pivot, roi=roi, contrast=1.0, strength=strength
            )
        else:
            eff_curve = float(tone_curve)
    else:
        eff_pivot, eff_curve = tone_pivot, tone_curve
    img = power_curve_raw(img, p=eff_pivot, k=eff_curve).astype(np.float32)

    # ── encode (same codecs as v1) ──────────────────────────────────────────
    if rotate_clockwise == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif rotate_clockwise == 180:
        img = cv2.rotate(img, cv2.ROTATE_180)
    elif rotate_clockwise == 270:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    img_bgr = cv2.cvtColor(np.clip(img, 0.0, 1.0), cv2.COLOR_RGB2BGR)
    if is_16bit_target:
        success, encoded_img = cv2.imencode(".tif", (img_bgr * 65535.0).astype(np.uint16))
    else:
        success, encoded_img = cv2.imencode(".png", (img_bgr * 255.0).astype(np.uint8))
    return encoded_img.tobytes() if success else None


def process_film_with_params(
    input_path,
    output_path,
    preset_mask_r,
    preset_mask_g,
    preset_mask_b,
    preset_gamma=1.0,
    preset_contrast=1.0,
    preset_contrast_r=1.0,
    preset_contrast_g=1.0,
    preset_contrast_b=1.0,
    rotate_clockwise=0,
    wp_roi_x1=None,
    wp_roi_y1=None,
    wp_roi_x2=None,
    wp_roi_y2=None,
    area_basis_w=None,
    area_basis_h=None,
    white_balance="auto",
    exposure_ev_mode="3ev",
    exposure_ev=0.0,
    tone_pivot=0.5,
    tone_curve=0.5,
    color_mode="skin_protect",
    dust=None,
    dust_rois=None,
    algo="v1",
    saturation=1.0,
):
    # 1. Read input file as byte stream
    try:
        with open(input_path, "rb") as f:
            input_bytes = f.read()
    except Exception as e:
        print(f"Error: Cannot read input file '{input_path}': {e}")
        return

    # Support raw format toggle, check file extension
    ext = input_path.suffix.lower()

    # 2. Call byte stream processing function
    output_bytes = process_film_bytestream_with_params(
        input_bytes,
        preset_mask_r=preset_mask_r,
        preset_mask_g=preset_mask_g,
        preset_mask_b=preset_mask_b,
        preset_gamma=preset_gamma,
        preset_contrast=preset_contrast,
        preset_contrast_r=preset_contrast_r,
        preset_contrast_g=preset_contrast_g,
        preset_contrast_b=preset_contrast_b,
        rotate_clockwise=rotate_clockwise,
        is_raw=ext in RAW_EXTENSIONS,
        wp_roi_x1=wp_roi_x1,
        wp_roi_y1=wp_roi_y1,
        wp_roi_x2=wp_roi_x2,
        wp_roi_y2=wp_roi_y2,
        area_basis_w=area_basis_w,
        area_basis_h=area_basis_h,
        white_balance=white_balance,
        exposure_ev_mode=exposure_ev_mode,
        exposure_ev=exposure_ev,
        tone_pivot=tone_pivot,
        tone_curve=tone_curve,
        color_mode=color_mode,
        dust=dust,
        dust_rois=dust_rois,
        algo=algo,
        saturation=saturation,
    )

    # 3. Write output byte stream to file
    if output_bytes is None:
        print(f"Error: Failed to process image from '{input_path}'")
        return

    try:
        with open(output_path, "wb") as f:
            f.write(output_bytes)
        print(f"Successfully saved to: {output_path}")
    except Exception as e:
        print(f"Error: Cannot write output file '{output_path}': {e}")
