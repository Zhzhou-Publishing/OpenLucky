# Changelog

## v1.4.0-rc2 (2026-04-08)

### Bug Fixes
- **Chinese File Path Support**: Fixed encoding issues when processing files with Chinese characters on Windows
  - Added `read_image_safe()` function using `np.fromfile` + `cv2.imdecode` to read images
  - Added `write_image_safe()` function using `np.tofile` to write images
  - Replaced `cv2.imread()` with `read_image_safe()` for Unicode path support in tool resize command
  - Resolves Windows command line encoding issues with non-ASCII file paths

### Technical Changes
- Enhanced `lib/tool/resize.py` with safe file I/O operations
- Improved cross-platform compatibility for file path handling

---

## Installation

For Windows users using the installer, simply run the `openlucky-setup.exe` file and follow the installation wizard.

For development or manual installation, please refer to the project documentation.

---

## Upgrade Notes

This release fixes a critical bug where the `tool resize` command failed to process files with Chinese characters in their paths on Windows. Users working with Chinese file paths should now be able to use all features without encoding issues.

---

## Known Issues

- No known issues in this release

---

## Contributors

- Ares

---

## Links

- [GitHub Repository](https://github.com/Zhzhou-Publishing/OpenLucky)
- [Issue Tracker](https://github.com/Zhzhou-Publishing/OpenLucky/issues)
