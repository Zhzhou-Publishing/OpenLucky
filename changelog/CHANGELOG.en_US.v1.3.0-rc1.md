# OpenLucky v1.3.0-rc1

## Features

### Save All Functionality
- Added Save All button in BottomMenuBar (sky blue, positioned right of Apply Preset)
- Implemented single file preset application (apply-preset-to-file)
- Implemented batch preset application (apply-preset-to-batch)
- Added global state management for isSaveAllClicked
- Added red dot indicator to all Save All buttons, controlled by isSaveAllClicked state
- Added Ctrl+S keyboard shortcut for Save All
- Disabled all controls during Save All process
- Optimized PhotoEdit page button disable states with isApplyingAll for batch operations
- Added logging for isSaveAllClicked state changes

### Preview Functionality
- Implemented preview feature with 5-second debounce on input changes
- Added applyPreview function (without isApplying logic)
- Added previewing state management (isPreviewing, previewingImages, presetLoaded)
- Added keydown event handling in NumberInput component
- Added i18n translations for previewing state (Chinese and English)
- Updated thumbnail loading state for previewing images
- Disabled apply/apply all buttons and input fields during previewing

### Image Resize Tool
- Added image resize tool with support for multiple formats and resize modes
- Improved image resize logic using openlucky tool resize command
- Added outputDirectory handling in PhotoDirectory and PhotoGallery

### Code Quality & Maintenance
- Added openlucky command execution logging in Electron main process
- Extracted image format constants to separate files for better maintainability
  - Created app/src/constants/imageFormats.js with IMAGE_EXTENSIONS, RAW_EXTENSIONS, TIFF_FORMATS
  - Created cmd/constants/image_formats.py with corresponding constants
- Removed unused imports from all Python files
- Updated all files to use centralized format constants
- Converted globalState to Vue reactive for immediate UI updates

## Bug Fixes

- Fixed sharp.sync error by using async/await with correct Sharp API
- Preserved directory parameters when returning from PhotoEdit to PhotoGallery
- Removed .preset.json copy functionality from apply operations

## Improvements

- Refactoring makes it easier to maintain and update supported image formats across the codebase
- Enhanced user feedback during Save All and preview operations
- Improved button state management for better user experience
