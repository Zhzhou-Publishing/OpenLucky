import tifffile
from pathlib import Path

from cli.constants.image_formats import TIFF_FORMATS


# Source compression name -> tifffile compression argument.
# Hasselblad/Imacon (Flextight) FFF files are big-endian TIFF containers whose
# main image is stored uncompressed; deflate is lossless and meaningfully
# shrinks 16-bit scans, so it is the default. 'none' is offered for software
# that chokes on compressed TIFF.
_COMPRESSION_MAP = {
    "none": None,
    "deflate": "deflate",
    "lzw": "lzw",
}

# Classic (non-Big) TIFF caps file offsets at 4 GiB. Switch to BigTIFF before
# we get close so long filmstrip scans (multi-GB) write correctly. Measured on
# the *uncompressed* payload because that bounds the worst case.
_BIGTIFF_THRESHOLD = 4_000_000_000


def _select_main_page(tif):
    """Return the full-resolution image page of an FFF/TIFF.

    FFF files carry the main scan plus small embedded thumbnail/preview pages.
    The main image is conventionally page 0, but we pick the largest page by
    pixel area so an unusual page order can't make us export a thumbnail.
    """
    return max(tif.pages, key=lambda p: int(p.shape[0]) * int(p.shape[1]))


def _read_resolution(page):
    """Extract (xres, yres, unit) DPI metadata from a TIFF page.

    Returns (None, None, None) when resolution tags are absent. TIFF stores
    X/YResolution as rationals; tifffile hands them back as (num, den) tuples
    or floats depending on version, so normalize both shapes to float.
    """
    def _rational(value):
        if value is None:
            return None
        if isinstance(value, (tuple, list)) and len(value) == 2:
            num, den = value
            return float(num) / float(den) if den else None
        return float(value)

    tags = page.tags
    xres = _rational(tags.valueof("XResolution")) if "XResolution" in tags else None
    yres = _rational(tags.valueof("YResolution")) if "YResolution" in tags else None
    unit = tags.valueof("ResolutionUnit") if "ResolutionUnit" in tags else None
    return xres, yres, unit


def fff_to_tiff(input_path, output_path, compression="deflate"):
    """Convert a Hasselblad/Imacon (Flextight) FFF scan to a standard TIFF.

    FFF is itself a big-endian TIFF container, so this is not a demosaic/RAW
    develop step (LibRaw does not read these scanner files). It extracts the
    full-resolution main image and re-saves it as a clean, single-page,
    widely-compatible TIFF -- dropping the embedded thumbnail/preview pages and
    Imacon-proprietary tags, while preserving bit depth (typically 16-bit RGB)
    and DPI. Switches to BigTIFF automatically for large (filmstrip) scans.

    Args:
        input_path: Path to the input .fff file.
        output_path: Path to the output TIFF file.
        compression: 'deflate' (default, lossless), 'lzw', or 'none'.

    Returns:
        bool: True if conversion succeeded, False otherwise.
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)

        if compression not in _COMPRESSION_MAP:
            print(f"Error: Unknown compression '{compression}'. "
                  f"Expected one of: {', '.join(_COMPRESSION_MAP)}")
            return False

        if not input_path.exists():
            print(f"Error: Input file does not exist: {input_path}")
            return False

        # Normalize output to a TIFF extension.
        if output_path.suffix.lower() not in TIFF_FORMATS:
            output_path = output_path.with_suffix(".tif")

        # 1. Read the full-resolution main page from the FFF container.
        with tifffile.TiffFile(str(input_path)) as tif:
            page = _select_main_page(tif)
            photometric = page.photometric
            xres, yres, unit = _read_resolution(page)
            img = page.asarray()

        # 2. Decide BigTIFF vs classic TIFF from the uncompressed payload size.
        use_bigtiff = img.nbytes >= _BIGTIFF_THRESHOLD

        # 3. Preserve photometric interpretation (RGB scans are photometric=2,
        #    but guard for the rare grayscale scan).
        photometric_arg = "rgb" if img.ndim == 3 and img.shape[2] >= 3 else "minisblack"

        write_kwargs = {
            "photometric": photometric_arg,
            "compression": _COMPRESSION_MAP[compression],
            "bigtiff": use_bigtiff,
        }
        # Carry DPI across when the source declared it.
        if xres and yres:
            write_kwargs["resolution"] = (xres, yres)
            if unit is not None:
                try:
                    write_kwargs["resolutionunit"] = int(unit)
                except (TypeError, ValueError):
                    pass

        # 4. Write the clean single-page TIFF.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(str(output_path), img, **write_kwargs)

        print(f"FFF to TIFF conversion successful: {output_path} "
              f"({img.shape[1]}x{img.shape[0]}, {img.dtype}, "
              f"{'BigTIFF' if use_bigtiff else 'TIFF'}, compression={compression})")
        return True

    except Exception as e:
        print(f"Error converting FFF to TIFF: {e}")
        import traceback

        traceback.print_exc()
        return False
