# v1.4.2-rc6

## New Features

- **Improved RAW Support**: RAW files are now properly handled when applying presets, with output automatically saved in the correct TIFF format.
- **Smarter File Recognition**: Photos with uppercase or mixed-case extensions (e.g. `.JPG`, `.NEF`, `.TIF`) are now recognized correctly.

## Performance

- **Faster Batch Processing**: Image processing now automatically uses all available CPU cores, significantly speeding up batch operations.

## Improvements

- **More Reliable Batch Save**: Saving multiple photos at once is now more stable, with clearer progress feedback for each file.
- **Smoother Photo Editing**: Simplified the editing state so buttons and badges respond more consistently while applying or saving.
- **Image Refresh Fix**: Resolved an issue that could cause processed images to reload unexpectedly.
