import io
import math
import rawpy
import numpy as np
import cv2

from cli.constants.image_formats import RAW_EXTENSIONS
from cli.lib.lut import apply_lut
from cli.lib.curve.s_curve import auto_pk, power_curve_raw
from cli.lib.process_film_functions.gamma_alignment import apply_midtone_alignment


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
):
    """
    Process byte stream image, supports RAW format toggle
    """
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
            gains[1] = awb_gains[1] * (1.0 + shift_y)  # 绿

    # --- 3.3 再次归一化 (防溢出) ---
    # 无论怎么调，确保最亮的那个通道在应用增益后刚好是 1.0
    # 这样可以维持曝光稳定，只改色调
    max_after_wb = np.max(white_point_vec * gains)
    gains /= max_after_wb + 1e-6

    # 应用增益
    img *= gains
    img = np.clip(img, 0, 1.0)

    # --- 插入中间调对齐逻辑 ---
    # 加法位移实现：在 sin² 权重下把每通道中位数朝目标拉近，幅度被 SHIFT_CAP
    # 截断；端点严格保留。user_ev_bias 仅在 mode='ev_target' 时起作用。
    img = apply_midtone_alignment(
        img,
        roi=(wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2),
        user_ev_bias=0.0,  # 拍摄意图需要另外传入参数！！！
    )

    # 调整曝光：走 LUT 通道，未命中时回退到原始函数。ev=0 时跳过避免量化损失。
    if exposure_ev != 0.0:
        img = apply_lut(
            f"common.apply-exposure-{exposure_ev_mode}",
            img,
            ev=exposure_ev,
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
    # 任一为 auto 就调一次 auto_pk，把手动那一侧的值塞进去覆盖。
    pivot_is_auto = (tone_pivot == 'auto')
    curve_is_auto = isinstance(tone_curve, str) and tone_curve.startswith('auto')
    if pivot_is_auto or curve_is_auto:
        strength = 1.0
        if isinstance(tone_curve, str) and tone_curve.startswith('auto:'):
            strength = float(tone_curve.split(':', 1)[1])
        roi = (
            (wp_roi_x1, wp_roi_y1, wp_roi_x2, wp_roi_y2)
            if roi_complete
            else None
        )
        # 手动 pivot 时传给 auto_pk 让 k 反解与之自洽；手动 curve 时丢掉 auto_k
        pivot_override = None if pivot_is_auto else float(tone_pivot)
        auto_p, auto_k = auto_pk(
            img, roi=roi, strength=strength, pivot=pivot_override
        )
        eff_pivot = auto_p  # = pivot_override when manual
        eff_curve = auto_k if curve_is_auto else float(tone_curve)
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
