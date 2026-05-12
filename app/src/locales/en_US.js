export default {
  navbar: {
    home: 'Home',
    about: 'About',
    leaveConfirm: 'Leaving this page will discard the images you have loaded. Continue?',
    closeConfirm: 'Unsaved changes will be lost if you close the window. Close anyway?'
  },
  photoDirectory: {
    title: 'Select Photo Directory',
    description: 'Choose a local folder containing your photos',
    installationError: '❌ The software installation is incomplete. This may be due to your antivirus software damaging the software. Please reinstall.',
    electronWarning: '⚠️ Not running in Electron environment',
    selectButton: '📁 Select Directory',
    loading: 'Loading...',
    selectedPath: 'Selected Path:',
    processingProgress: 'Preparing preview',
    compressPreview: 'Compress Preview',
    compressPreviewTip: 'Thumbnails will be compressed to 1920px width to speed up preview. This speeds up mask removal preview but slows down the loading process.',
    cancel: 'Cancel'
  },
  photoGallery: {
    back: '← Back',
    refresh: '🔄 Refresh',
    imagesCount: '{count} images',
    loading: 'Loading images...',
    noImages: 'No Images Found',
    noImagesDesc: 'No image files (jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf, or raf) were found in the selected directory.',
    applying: 'Applying...'
  },
  windowTitle: {
    baseTitle: 'OpenLucky Desktop App',
    applying: 'Applying',
    saving: 'Saving'
  },
  photoEdit: {
    back: '← Back',
    loading: 'Loading images...',
    noImages: 'No Images Found',
    noImagesDesc: 'No image files were found in the directory.',
    applying: 'Applying...',
    previewing: 'Previewing...',
    maskR: 'Mask-R',
    maskG: 'Mask-G',
    maskB: 'Mask-B',
    gamma: 'Gamma',
    contrast: 'Contrast',
    apply: 'Apply',
    applyAll: 'Apply All',
    basicTab: 'Basic Parameters',
    advancedTab: 'Emulsion Concentration Correction',
    exposureTab: 'Exposure',
    toneTab: 'Tone Adjustment',
    tonePivot: 'Exposure Pivot',
    toneCurve: 'Exposure Contrast',
    tonePivotLeft: 'Shift Left',
    tonePivotRight: 'Shift Right',
    toneCurveLeft: 'Lower Contrast',
    toneCurveRight: 'Raise Contrast',
    whiteBalanceTab: 'White Balance',
    whiteBalanceAuto: 'Auto',
    whiteBalanceTemp: 'Temperature',
    whiteBalanceTint: 'Tint',
    contrastR: 'Contrast R',
    contrastG: 'Contrast G',
    contrastB: 'Contrast B',
    contextMenu: {
      copyParams: 'Copy Parameters',
      pasteParams: 'Paste Parameters',
      applyPreset: 'Apply Preset',
      pickMaskColor: 'Pick Mask Color',
      pickWhitePointArea: 'Select White-Point Area',
      clearWhitePointArea: 'Clear White-Point Area',
      rotate: 'Rotate',
      rotateClockwise: 'Clockwise 90°',
      rotateCounterClockwise: 'Counter-clockwise 90°',
      rotate180: 'Rotate 180°',
      resetImage: 'Reset Image'
    },
    eyedropper: {
      exitHint: 'Eyedropper active — click the image to pick, press ESC to cancel'
    },
    areaSelect: {
      exitHint: 'Area-select active — drag from top-left to bottom-right, press ESC to cancel'
    },
    applyPresetModal: {
      title: 'Select a Preset',
      save: 'Apply',
      pickColor: 'Pick Mask Color'
    }
  },
  bottomMenu: {
    preset: 'Preset:',
    apply: 'Apply',
    applying: 'Applying...'
  },
  saveAllButton: {
    saveAll: 'Save All',
    unappliedTooltip: "Some images don't have parameters applied yet"
  },
  about: {
    title: 'About OpenLucky Desktop',
    version: 'Version Information',
    description: 'Description',
    descriptionText: 'OpenLucky Desktop is a powerful desktop application for film processing and batch operations. Built with Electron and Vue 3, it provides a modern and efficient user interface for managing your workflow.',
    homepage: 'Homepage',
    license: 'License',
    licenseSummary: 'Permits commercial use, modification, distribution, and private use; requires preserving the copyright notice and stating any significant changes; does not grant trademark rights and provides no warranty.',
    language: 'Language',
    theme: 'Theme',
    themeLight: 'Light',
    themeDark: 'Dark'
  }
}
