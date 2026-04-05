# OpenLucky v1.2.2-rc1 Release Notes

## Summary
This release includes several bug fixes and feature improvements focused on directory handling, preset synchronization, and temporary file management.

## Changes

### Bug Fixes
- **Fix page title display**: PhotoGallery and PhotoEdit pages now display the selected original directory name in titles instead of the working directory name, providing better user context
- **Fix affectedImages removal logic**: Corrected the issue where the affectedImages set was not being properly cleared after successful film parameter application by correctly extracting filenames from the backend response
- **Fix filmparam output path issue**: Resolved path issues where the application was using directory paths instead of proper file paths
- **Improve temporary file cleanup**: Replaced manual filesystem operations with tmp.dirSync to ensure consistent cleanup of temporary files on application exit, preventing accumulation in the system temp directory

### Features
- **Implement temp directory refactoring**: Moved temporary directory processing from PhotoGallery to PhotoDirectory for better separation of concerns
- **Add .preset.json synchronization**: Implemented functionality to copy .preset.json from working directory back to original directory after apply operations, ensuring user settings are preserved
- **Support output_dir from preset.json**: Enhanced full-res image loading to support loading processed images from their output directories as specified in preset.json
- **Add prepare-working-directory IPC handler**: Created new IPC handlers for improved temp directory management

### Improvements
- **Add standard-version**: Integrated standard-version for automated changelog generation
- **Refactor openlucky.py**: Removed unused filmbytes command processing logic and fixed config file reading in film command
- **Improve user feedback during preset apply**: Added hourglass cursor and disabled thumbnails during preset application in PhotoGallery to provide better visual feedback
- **Maintain backward compatibility**: Ensured existing routes continue to work with the new directory handling approach

## Technical Details

### Backend Changes
- Updated PhotoDirectory IPC handler to support prepare-working-directory-from-selected
- Added copy-preset-json IPC handler for synchronization
- Modified get-full-res-image to support output_dir parameter
- Removed hardcoded working temp directory logic in favor of tmp.dirSync

### Frontend Changes
- PhotoGallery: Updated title computation to use originalDirectoryPath instead of workingDirectory
- PhotoEdit: Updated title computation to use originalDirectory instead of workingDirectory
- PhotoEdit: Fixed affectedImages logic with proper filename extraction from backend responses
- Both pages: Added preset.json synchronization calls after apply operations

## Compatibility
- Backward compatible with existing routes
- Requires updated Electron main.js for new IPC handlers
