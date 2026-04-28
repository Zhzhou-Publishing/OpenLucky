import rawpy
import cv2
from pathlib import Path

from cli.constants.image_formats import TIFF_FORMATS


def raw_to_tiff(input_path, output_path):
    """
    Convert RAW format image to TIFF format

    Args:
        input_path: Path to input RAW file (supports .arw, .cr2, .cr3, .nef, .dng, .orf, .raf)
        output_path: Path to output TIFF file

    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Check if output_path has valid TIFF extension
        if output_path.suffix.lower() not in TIFF_FORMATS:
            output_path = output_path.with_suffix(".tif")

        # 1. Read RAW file using rawpy
        with rawpy.imread(str(input_path)) as raw:
            # Determine demosaic algorithm based on camera format
            # Fuji .RAF files use DHT, other formats use AAHD
            if input_path.suffix.lower() == ".raf":
                # Use DHT algorithm for Fuji RAF files
                demosaic_algorithm = rawpy.DemosaicAlgorithm.DHT
            else:
                # Use AAHD algorithm (ID 12) for other formats
                # Suitable for cameras without low-pass filter, sharper grain texture
                demosaic_algorithm = rawpy.DemosaicAlgorithm.AAHD

            # 2. Postprocess with specified parameters
            img = raw.postprocess(
                # Demosaic algorithm (DHT for Fuji RAF, AAHD for others)
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
            )

        # 3. Convert to BGR for OpenCV encoding (rawpy outputs RGB)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # 4. Encode to TIFF
        success, encoded_img = cv2.imencode(".tif", img_bgr)

        if not success:
            print(f"Failed to encode TIFF: {output_path}")
            return False

        # 5. Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(encoded_img.tobytes())

        print(f"RAW to TIFF conversion successful: {output_path}")
        return True

    except Exception as e:
        print(f"Error converting RAW to TIFF: {e}")
        import traceback

        traceback.print_exc()
        return False
