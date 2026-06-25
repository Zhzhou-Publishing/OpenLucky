"""
Image format constants for OpenLucky
"""

# Common image file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif', '.webp'}

# RAW camera file extensions
RAW_EXTENSIONS = {'.arw', '.cr2', '.cr3', '.nef', '.dng', '.orf', '.raf'}

# Hasselblad/Imacon (Flextight) scanner file extensions.
# These are big-endian TIFF containers, not Bayer RAW -- handled via tifffile,
# not LibRaw. Kept separate from RAW_EXTENSIONS so the RAW develop path is not
# applied to them.
FFF_EXTENSIONS = {'.fff'}

# TIFF file extensions
TIFF_FORMATS = {'.tif', '.tiff'}
