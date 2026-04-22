# OpenLucky v1.4.2-rc9

## Improvements

- **Reduced UI Lag During File Preparation**: Replaced concurrent file processing with sequential await-based processing when preparing the working directory. RAW files are processed first, followed by non-RAW files, resulting in a more responsive UI.
