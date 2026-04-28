import io
import rawpy
import numpy as np
import cv2

from cli.constants.image_formats import RAW_EXTENSIONS


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

    # 2. Remove color mask (operate in 0-1 space)
    # At this point, img is confirmed to be in RGB order
    img[:, :, 0] /= preset_mask_r / 255.0  # Red
    img[:, :, 1] /= preset_mask_g / 255.0  # Green
    img[:, :, 2] /= preset_mask_b / 255.0  # Blue
    img = np.clip(img, 0, 1.0)

    # 3. Color inversion (in 0-1 space, it's 1.0 - img)
    img = 1.0 - img

    # 4. Gamma correction
    # For linear RAW, input around 0.45 is recommended; for gamma-corrected images, around 1.0 for fine-tuning
    if preset_gamma != 1.0:
        # Perform power operation in 0-1 space for maximum precision
        img = np.power(img, preset_gamma)

    # 5. Auto levels and contrast fine-tuning
    # Store per-channel contrast settings in a list for iteration
    channel_contrasts = [preset_contrast_r, preset_contrast_g, preset_contrast_b]
    
    for i in range(3):
        low = np.percentile(img[:, :, i], 0.5)
        high = np.percentile(img[:, :, i], 99.5)
        # Apply combined contrast: global * channel_specific
        combined_contrast = preset_contrast * channel_contrasts[i]
        # Linear stretch and apply contrast
        img[:, :, i] = np.clip(
            (img[:, :, i] - low) * (1.0 / (high - low + 1e-5)) * combined_contrast, 0, 1.0
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
