# OpenLucky Desktop App - Update Log (feature/desktop-app)

## Version v1.2.0-rc1

This release brings the complete desktop application experience with film processing capabilities, preset management, and a polished user interface.

---

## New Features

### Desktop Application
- **Electron Desktop App**: Complete desktop application with Vue.js UI for a seamless user experience
- **Custom Application Icon**: OpenLucky branding with custom icon resources (.ico and .png formats)
- **Window Management**: Fixed window size with auto-hide menu bar, resizable toggles, and developer tools control
- **Windows Installer**: Inno Setup configuration for creating professional Windows installers with desktop and Start Menu shortcuts
- **Build System**: Complete build infrastructure for both portable and installer versions

### Photo Gallery and Navigation
- **Photo Gallery Page**: Browse images from selected directories with thumbnail grid layout
- **Directory Selection**: Built-in directory picker with file listing display
- **Thumbnail Generation**: Automatic thumbnail generation with sharp library, supporting multiple image formats including TIF/TIFF
- **Image Modal**: Full-screen image viewing with right-click trigger
- **Keyboard Navigation**: Navigate between images using arrow keys and bracket keys

### Film Processing
- **Custom Parameters Processing**: New `filmparam` and `filmparambatch` commands for processing with custom parameters
  - Supports custom mask_r, mask_g, mask_b, gamma, and contrast values
  - Batch processing capability for entire directories
- **Preset Management**:
  - Automatic preset saving to `.preset.json` with timestamp format
  - Dynamic preset loading with `.preset.json` support
  - Preset application with real-time updates
  - Separate working and preview directories for better workflow
- **Processing Feedback**: Loading states and animations during preset application

### PhotoEdit Page
- **Full Resolution Image Viewer**: View and edit high-resolution images with parameter controls
- **NumberInput Component**: Custom input component with increment/decrement buttons and keyboard shortcuts
  - 5 parameter controls: Mask-R, Mask-G, Mask-B, Gamma, Contrast
  - Configurable step values for fine-tuned adjustments
  - Keyboard shortcut tooltips for accessibility
- **Apply Buttons**:
  - Apply button for single image processing (Enter key)
  - Apply All button for batch processing (Ctrl+Enter)
  - Visual feedback during processing operations
  - Disabled state management during operations
- **Instant Updates**: Image updates with cache bypassing using timestamps (no loading overlays)
- **Window Resizing**: Dynamic window resizing capability when entering/leaving gallery view

### User Interface
- **Bottom Menu Bar**: Preset selector with apply button and visual indicator
- **Feature Cards**: Home page with navigation cards for different features
- **Navbar**: Clean navigation with Home and About links
- **Responsive Design**: Adaptive layouts and spacing

### Keyboard Shortcuts
- **Global Shortcuts**:
  - Arrow keys: Navigate between images
  - [ / ]: Navigate between images (alternative)
  - Enter: Apply current settings
  - Ctrl+Enter: Apply to all images
- **Parameter Controls**:
  - Q/A: Increase/Decrease Mask-R
  - W/S: Increase/Decrease Mask-G
  - E/D: Increase/Decrease Mask-B
  - R/F: Increase/Decrease Gamma (small step)
  - T/G: Increase/Decrease Contrast (small step)
  - Alt+Shift+R/F: Increase/Decrease Gamma (large step)
  - Alt+Shift+T/G: Increase/Decrease Contrast (large step)

### Config and Installation
- **Config Command**: Read application configuration
- **Installation Check**: Verify openlucky CLI availability before enabling features
- **Environment Documentation**: Complete build instructions in BUILD.md
- **Python Support**: Documentation for PYTHONPATH requirements

---

## Improvements

### Performance
- **Parallel Loading**: Load images and presets in parallel using Promise.all
- **Caching**: Image URL timestamps to bypass Electron's built-in browser cache
- **Loading States**: Visual indicators during async operations

### User Experience
- **Visual Feedback**: Red dot indicator for unapplied presets
- **Animations**: Slide-up animation for bottom menu
- **Disabled States**: Controls properly disabled during operations
- **Error Handling**: Graceful error messages and fallback states
- **Accessibility**: Keyboard shortcuts work across all inputs and controls

### Code Quality
- **Component Structure**: Reusable components (NumberInput, FeatureCard, Navbar)
- **State Management**: Clean reactive state with Vue 3 Composition API
- **IPC Communication**: Robust inter-process communication between main and renderer
- **Type Safety**: Consistent prop types and validation

---

## Bug Fixes

- **Scrolling Support**: Fixed scrolling issues in thumbnail gallery
- **Icon Consistency**: Updated icon filename references to OpenLuckyApp.exe
- **Module Imports**: Added lib. prefix to Python module imports
- **Path Handling**: Use forward slashes in JSON paths to avoid double backslashes
- **DevTools Control**: Prevent automatic DevTools opening in production builds
- **Window Blocking**: Hide preview windows to prevent execution blocking
- **Image Modal Trigger**: Changed to right-click only for better UX
- **Browser Default Inputs**: Removed default spin buttons from number inputs
- **Shortcut Key Handling**: Fixed keyboard shortcuts to work when inputs are focused
- **Preset Application**: Improved preset loading and application logic

---

## Technical Details

### Dependencies Added
- **electron**: Desktop app framework
- **electron-builder**: Application packaging
- **vue-router**: Client-side routing
- **sharp**: Image processing and thumbnail generation

### Build System
- **npm scripts**: Build commands for both CLI and desktop app
- **electron-builder config**: Windows packaging configuration
- **Inno Setup**: Professional Windows installer creation
- **.gitignore**: Proper exclusions for build artifacts

### File Structure
```
app/                          # Electron application
├── src/
│   ├── components/           # Vue components
│   │   ├── NumberInput.vue
│   │   ├── Navbar.vue
│   │   └── FeatureCard.vue
│   ├── pages/              # Vue pages
│   │   ├── Home.vue (removed)
│   │   ├── PhotoDirectory.vue
│   │   ├── PhotoGallery.vue
│   │   └── PhotoEdit.vue
│   ├── App.vue
│   └── main.js
├── package.json
└── (built files)

dist-electron/              # Built Electron app
├── win-unpacked/
└── (installer files)
```

### Configuration Files
- **OpenLucky.iss**: Inno Setup installer configuration
- **app/package.json**: Electron app configuration
- **.preset.json**: Runtime preset storage (generated)
- **presets.sample.json**: Preset format reference

---

## Migration Notes

### From v1.1.0-pre2 to v1.2.0-rc1
- Desktop app installation includes new icons and shortcuts
- Preset format updated to include timestamp metadata
- Keyboard shortcuts updated to support sticky key combinations
- Image caching behavior changed - images now update instantly

### Breaking Changes
- None - this release is backwards compatible with existing CLI usage

---

## Future Plans

- Additional film processing features
- Advanced preset management
- Batch operation improvements
- More keyboard shortcut customization
- Export/import configuration
- Analytics and usage tracking

---

**Built with**: Electron + Vue.js + openlucky CLI
**Platform**: Windows (with future Linux/macOS support planned)
**Release Date**: 2026
