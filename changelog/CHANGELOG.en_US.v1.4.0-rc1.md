# Changelog

## v1.4.0-rc1 (2026-04-07)

### Features
- **PhotoEdit Layout Restructuring**: Complete redesign of the PhotoEdit page with a new frame layout
  - Moved thumbnail navigation to the left side with vertical scrolling
  - Implemented fixed header at the top and fixed operation area at the bottom
  - Main image display area with strict height constraints
  - Support for mouse wheel scrolling in thumbnail list
  - Thumbnails container extends from header to page bottom
  - Image container strictly limited to avoid overlapping with operation area

### Improvements
- **Navigation Controls**: Updated keyboard shortcuts for image navigation
  - Added up/down arrow keys for changing images
  - Removed left/right arrow keys and bracket shortcuts
  - Improved keyboard navigation experience

### Bug Fixes
- Fixed window title updates during preset application and save operations
- Improved window title synchronization across different operations

### Technical Changes
- Refactored PhotoEdit.vue component structure
- Updated CSS layout system for better responsiveness
- Enhanced thumbnail scrolling behavior
- Improved image display positioning and sizing

### Documentation
- Added PR documentation for PhotoEdit layout restructuring (pr/011.photo_edit_new_frame.md)
- Added PR documentation for window title feature (pr/010.title_status.md)

---

## Installation

For Windows users using the installer, simply run the `openlucky-setup.exe` file and follow the installation wizard.

For development or manual installation, please refer to the project documentation.

---

## Upgrade Notes

This release includes significant changes to the PhotoEdit page layout. Users accustomed to the previous layout may notice:
- Thumbnails now appear on the left side instead of the bottom
- Navigation controls have moved to the bottom of the screen
- Keyboard shortcuts have changed (use up/down arrows instead of left/right)

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
