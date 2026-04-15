<template>
  <div class="photo-gallery-page">
    <div class="header">
      <button @click="goBack" class="back-button">{{ $t('photoGallery.back') }}</button>
      <h1 class="page-title">{{ title }}</h1>
      <button @click="handleRefresh" class="refresh-button" :disabled="isLoading">
        {{ $t('photoGallery.refresh') }}
      </button>
      <span class="count-badge">{{ $t('photoGallery.imagesCount', { count: images.length }) }}</span>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ $t('photoGallery.loading') }}</p>
    </div>

    <div v-else-if="images.length === 0" class="empty-state">
      <p class="empty-icon">📷</p>
      <h2>{{ $t('photoGallery.noImages') }}</h2>
      <p>{{ $t('photoGallery.noImagesDesc') }}</p>
    </div>

    <div v-else class="gallery-grid">
      <div
        v-for="(image, index) in images"
        :key="index"
        class="image-item"
        :class="{ 'applying': isApplyingPreset, 'cursor-wait': isSavingAll }"
        @click="!isSavingAll && openPhotoEdit(image)"
        @contextmenu.prevent="!isSavingAll && openImage(image)"
      >
        <img :src="image.url" :alt="image.name" class="thumbnail" loading="lazy" />
        <div class="image-info">
          <p class="image-name">{{ image.name }}</p>
        </div>
      </div>
    </div>

    <!-- Bottom Menu Bar -->
    <BottomMenuBar
      ref="bottomMenuBarRef"
      :selected-preset="selectedPreset"
      :has-unapplied-changes="hasUnappliedChanges"
      :is-loading="isLoading"
      :is-applying-preset="isApplyingPreset"
      :is-saving-all="isSavingAll"
      :images-count="images.length"
      @update:selected-preset="selectedPreset = $event"
      @apply="applyPreset"
      @save-all="saveAll"
      @presets-loaded="handlePresetsLoaded"
    />

    <!-- Image Modal -->
    <div v-if="selectedImage" class="modal" @click="closeModal">
      <div class="modal-content" @click.stop>
        <button @click="closeModal" class="close-button">×</button>
        <img :src="selectedImage.url" :alt="selectedImage.name" class="modal-image" />
        <p class="modal-filename">{{ selectedImage.name }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import BottomMenuBar from '../components/BottomMenuBar.vue'
import { setSaveAllClicked } from '../utils/globalState'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

// Get path module from Node.js in Electron
let path = null
if (window.require) {
  path = window.require('path')
}

const images = ref([])
const isLoading = ref(true)
const selectedImage = ref(null)
const selectedPreset = ref('lucky_c200_2025')
const hasUnappliedChanges = ref(true)
const isApplyingPreset = ref(false)
const isSavingAll = ref(false)
const workingDirectory = ref('')
const outputDirectory = ref('')
const originalDirectoryPath = ref('')
const originalWindowTitle = ref('OpenLucky Desktop App')

const directoryPath = computed(() => route.query.workingDirectory || route.query.path || '')

const title = computed(() => {
  if (originalDirectoryPath.value) {
    const parts = originalDirectoryPath.value.split(/[/\\]/)
    return parts[parts.length - 1] || 'Photo Gallery'
  }
  return 'Photo Gallery'
})

const goBack = () => {
  // If we came from PhotoEdit, go back to PhotoGallery (current page) with the same parameters
  // Otherwise, go back to PhotoDirectory
  router.push('/photo-directory')
}

const openImage = (image) => {
  selectedImage.value = image
}

const openPhotoEdit = (image) => {
  // Prevent navigation when applying preset
  if (isApplyingPreset.value) {
    return
  }

  router.push({
    path: '/photo-edit',
    query: {
      workingDirectory: workingDirectory.value,
      outputDirectory: outputDirectory.value,
      originalDirectory: originalDirectoryPath.value,
      filename: image.name,
      appliedPresetKey: selectedPreset.value
    }
  })
}

const closeModal = () => {
  selectedImage.value = null
}

const applyPreset = async () => {
  try {
    // Reset global isSaveAllClicked state
    setSaveAllClicked(false)

    // Save original window title
    originalWindowTitle.value = document.title

    // Update window title with "Applying" suffix
    document.title = `${t('windowTitle.baseTitle')} - ${t('windowTitle.applying')}`

    isApplyingPreset.value = true
    hasUnappliedChanges.value = false

    // Check if running in Electron
    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      // Remove existing listeners to avoid duplicates
      ipcRenderer.removeAllListeners('preset-apply-started')
      ipcRenderer.removeAllListeners('preset-apply-progress')
      ipcRenderer.removeAllListeners('preset-apply-success')
      ipcRenderer.removeAllListeners('preset-apply-error')

      // Listen for apply started
      ipcRenderer.once('preset-apply-started', (_, result) => {
        console.log('Preset apply started:', result.message)
      })

      // Listen for progress updates
      ipcRenderer.on('preset-apply-progress', (_, result) => {
        console.log('Progress:', result.data)
      })

      // Listen for success
      ipcRenderer.once('preset-apply-success', async (_, result) => {
        console.log('Preset applied successfully:', result.message)
        isApplyingPreset.value = false

        // Restore original window title
        document.title = originalWindowTitle.value

        // Wait a moment for the .preset.json to be updated
        await new Promise(resolve => setTimeout(resolve, 1000))

        // Refresh images to show from .preset.json output_dir
        loadImages()
      })

      // Listen for errors
      ipcRenderer.once('preset-apply-error', (_, result) => {
        console.error('Error applying preset:', result.message)
        if (result.error) {
          console.error('Error details:', result.error)
        }
        isApplyingPreset.value = false

        // Restore original window title
        document.title = originalWindowTitle.value
      })

      // Send request to main process
      ipcRenderer.send('apply-preset', {
        inputPath: workingDirectory.value,
        outputPath: outputDirectory.value,
        preset: selectedPreset.value
      })
    } else {
      // Fallback for non-Electron environment
      console.warn('Not running in Electron, cannot apply preset')
      isApplyingPreset.value = false

      // Restore original window title
      document.title = originalWindowTitle.value
    }
  } catch (error) {
    console.error('Error applying preset:', error)
    isApplyingPreset.value = false

    // Restore original window title
    document.title = originalWindowTitle.value
  }
}

watch(selectedPreset, () => {
  hasUnappliedChanges.value = true
})

const loadImages = async () => {
  try {
    isLoading.value = true
    if (!workingDirectory.value) {
      router.push('/photo-directory')
      return
    }

    // Check if running in Electron
    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      // Request images from main process, pass workingDirectory
      ipcRenderer.send('get-images', workingDirectory.value)

      ipcRenderer.once('images-loaded', (_, result) => {
        images.value = result.images
        isLoading.value = false
      })

      ipcRenderer.once('images-error', (_, error) => {
        console.error('Error loading images:', error)
        isLoading.value = false
      })
    } else {
      // Fallback for non-Electron environment
      console.warn('Not running in Electron, showing demo data')
      isLoading.value = false
    }
  } catch (error) {
    console.error('Error loading images:', error)
    isLoading.value = false
  }
}

const handleRefresh = async () => {
  await loadImages()
}

const handlePresetsLoaded = (presets) => {
  // Select first preset by default if available
  if (presets && presets.length > 0 && !presets.find(p => p.value === selectedPreset.value)) {
    selectedPreset.value = presets[0].value
  }
}

const saveAll = async () => {
  if (!workingDirectory.value || !originalDirectoryPath.value) {
    console.error('No working directory or original directory')
    return
  }

  if (!window.require) {
    console.error('Not running in Electron')
    return
  }

  // Set global isSaveAllClicked state
  setSaveAllClicked(true)

  // Save original window title
  originalWindowTitle.value = document.title

  // Update window title with initial "Saving" suffix
  document.title = `${t('windowTitle.baseTitle')} - ${t('windowTitle.saving')}`

  try {
    const ipcRenderer = window.require('electron').ipcRenderer

    // Set saving all state to disable controls
    isSavingAll.value = true

    // Remove existing listeners to avoid duplicates
    ipcRenderer.removeAllListeners('preset-to-file-started')
    ipcRenderer.removeAllListeners('preset-to-file-progress')
    ipcRenderer.removeAllListeners('preset-to-file-success')
    ipcRenderer.removeAllListeners('preset-to-file-error')

    // Prepare the output directory path
    const outputDir = path.join(originalDirectoryPath.value, 'output')

    // Ensure output directory exists
    const fs = window.require('fs')
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true })
    }

    // Process each file individually
    const filesToProcess = images.value.map(img => img.name)
    let processedCount = 0
    let successCount = 0
    let errorCount = 0

    // Process files sequentially
    for (const filename of filesToProcess) {
      // Update window title with current file being processed
      const filePath = path.join(originalDirectoryPath.value, filename)
      document.title = `${t('windowTitle.baseTitle')} - ${t('windowTitle.saving')} ${filePath} [${processedCount + 1}/${filesToProcess.length}]`

      // Send request to main process for each file
      const presetFile = path.join(workingDirectory.value, '.preset.json')
      const outputFilePath = path.join(outputDir, filename)

      try {
        await new Promise((resolve) => {
          // Handle started
          const startedHandler = (_, result) => {
            console.log(result.message)
          }
          ipcRenderer.once('preset-to-file-started', startedHandler)

          // Handle success
          const successHandler = (_, result) => {
            console.log(result.message)
            successCount++
            resolve()
          }
          ipcRenderer.once('preset-to-file-success', successHandler)

          // Handle error
          const errorHandler = (_, result) => {
            console.error('Error processing file:', filename, result.message, result.error)
            errorCount++
            resolve() // Continue with next file even if this one fails
          }
          ipcRenderer.once('preset-to-file-error', errorHandler)

          // Send request
          ipcRenderer.send('apply-preset-to-file', {
            presetFile: presetFile,
            inputFilePath: filePath,
            outputFilePath: outputFilePath
          })
        })
      } catch (error) {
        console.error('Error processing file:', filename, error)
        errorCount++
      }

      processedCount++
    }

    // Restore original window title
    document.title = originalWindowTitle.value
    isSavingAll.value = false

    // Reload images to show updated status
    loadImages()

    // Log summary
    console.log(`Save all completed: ${successCount} succeeded, ${errorCount} failed, ${processedCount} total`)
  } catch (error) {
    console.error('Error saving all files:', error)
    isSavingAll.value = false

    // Restore original window title
    document.title = originalWindowTitle.value
  }
}

onMounted(() => {
  // Initialize window title
  originalWindowTitle.value = t('windowTitle.baseTitle')
  document.title = originalWindowTitle.value

  // Make window resizable when entering photo gallery
  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.send('set-window-resizable', true)

    // Check if working directory was provided by PhotoDirectory
    if (route.query.workingDirectory) {
      // Use the provided working directory directly
      workingDirectory.value = route.query.workingDirectory
      originalDirectoryPath.value = route.query.originalDirectory || ''
      // Use the outputDirectory from query if available, otherwise compute it
      if (route.query.outputDirectory) {
        outputDirectory.value = route.query.outputDirectory
      } else {
        outputDirectory.value = path.join(workingDirectory.value, 'output')
      }
      loadImages()
    } else {
      // Fallback to old behavior for backward compatibility
      originalDirectoryPath.value = directoryPath.value
      ipcRenderer.send('prepare-working-directory', directoryPath.value)

      ipcRenderer.once('working-directory-prepared', (_, result) => {
        workingDirectory.value = result.workingDirectory
        // Use the outputDirectory from result if available, otherwise compute it
        if (result.outputDirectory) {
          outputDirectory.value = result.outputDirectory
        } else {
          outputDirectory.value = path.join(workingDirectory.value, 'output')
        }
        loadImages()
      })

      ipcRenderer.once('working-directory-error', (_, error) => {
        console.error('Error preparing working directory:', error)
        isLoading.value = false
      })
    }
  }

  // Add Ctrl+S keyboard shortcut
  const handleKeydown = (event) => {
    if ((event.key === 's' || event.key === 'S') && event.ctrlKey) {
      event.preventDefault()
      saveAll()
    }
  }
  window.saveAllKeydownHandler = handleKeydown
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  // Make window non-resizable when leaving photo gallery
  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.send('set-window-resizable', false)
  }

  // Restore original window title
  document.title = originalWindowTitle.value

  // Remove keyboard event listener
  if (window.saveAllKeydownHandler) {
    window.removeEventListener('keydown', window.saveAllKeydownHandler)
    delete window.saveAllKeydownHandler
  }
})
</script>

<style scoped>
.photo-gallery-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20px;
  padding-bottom: 140px;
  overflow-y: auto;
  height: calc(100vh - 100px);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.back-button {
  padding: 10px 20px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s ease;
}

.back-button:hover {
  background: #35a372;
}

.refresh-button {
  padding: 10px 20px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s ease;
  margin-right: 10px;
}

.refresh-button:hover:not(:disabled) {
  background: #35a372;
}

.refresh-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-title {
  font-size: 24px;
  color: #333;
  margin: 0;
  flex: 1;
  text-align: center;
}

.count-badge {
  padding: 6px 12px;
  background: #42b883;
  color: white;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #666;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #42b883;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 16px;
  color: #666;
  max-width: 400px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 20px;
}

.image-item {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.image-item:hover:not(.applying) {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.image-item.applying {
  cursor: wait;
  opacity: 0.7;
}

.image-item.cursor-wait {
  cursor: wait;
}

.thumbnail {
  width: 100%;
  height: 100px;
  object-fit: cover;
  display: block;
}

.image-info {
  padding: 12px;
}

.image-name {
  font-size: 14px;
  color: #333;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

.modal-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
}

.close-button {
  position: absolute;
  top: -40px;
  right: 0;
  background: transparent;
  color: white;
  border: none;
  font-size: 36px;
  cursor: pointer;
  padding: 0;
  width: 40px;
  height: 40px;
  line-height: 40px;
}

.modal-image {
  max-width: 100%;
  max-height: calc(90vh - 40px);
  object-fit: contain;
  border-radius: 4px;
}

.modal-filename {
  margin-top: 15px;
  color: white;
  text-align: center;
  font-size: 14px;
}
</style>
