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
      :has-unapplied-images="hasUnappliedImages"
      @update:selected-preset="selectedPreset = $event"
      @apply="applyPreset"
      @save-all="saveAll"
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
import { presets as globalPresets } from '../utils/presetCache'

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
const presetsData = ref({})
const presetsDataLoaded = ref(false)
const compressPreview = ref(false)

// Block SaveAll until every image has an entry in .preset.json. Until we
// finish reading the file we keep SaveAll disabled to be safe.
const hasUnappliedImages = computed(() => {
  if (!images.value.length) return false
  if (!presetsDataLoaded.value) return true
  return images.value.some(img => !presetsData.value[img.name])
})

const loadPresetJson = () => {
  if (!workingDirectory.value || !window.require) return
  const ipcRenderer = window.require('electron').ipcRenderer
  ipcRenderer.send('read-preset-json', workingDirectory.value)
  ipcRenderer.once('preset-json-loaded', (_, result) => {
    presetsData.value = result.presets || {}
    presetsDataLoaded.value = true
  })
  ipcRenderer.once('preset-json-error', () => {
    presetsDataLoaded.value = true
  })
}

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
        loadPresetJson()
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

// Default the selected preset to the first available entry whenever the
// global preset list changes, including the initial pre-load.
watch(globalPresets, (list) => {
  if (list && list.length > 0 && !list.find(p => p.value === selectedPreset.value)) {
    selectedPreset.value = list[0].value
  }
}, { immediate: true })

const saveAll = () => {
  if (hasUnappliedImages.value) {
    console.warn('SaveAll blocked: there are still images without applied parameters')
    return
  }
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
    ipcRenderer.removeAllListeners('preset-to-batch-started')
    ipcRenderer.removeAllListeners('preset-to-batch-progress')
    ipcRenderer.removeAllListeners('preset-to-batch-success')
    ipcRenderer.removeAllListeners('preset-to-batch-error')

    // Prepare the output directory path
    const outputDir = path.join(originalDirectoryPath.value, 'output')

    // Send request to main process
    ipcRenderer.send('apply-preset-to-batch', {
      presetFile: path.join(workingDirectory.value, '.preset.json'),
      inputDir: originalDirectoryPath.value,
      outputDir: outputDir
    })

    // Handle started
    ipcRenderer.once('preset-to-batch-started', (_, result) => {
      console.log(result.message)
    })

    // Handle progress - update window title with current file being processed
    ipcRenderer.on('preset-to-batch-progress', (_, result) => {
      console.log(result.data)

      // Update window title with current file path being processed
      if (result.file) {
        const filePath = path.join(originalDirectoryPath.value, result.file)
        document.title = `${t('windowTitle.baseTitle')} - ${t('windowTitle.saving')} ${filePath}`
      }
    })

    // Handle success
    ipcRenderer.once('preset-to-batch-success', (_, result) => {
      console.log(result.message)
      isSavingAll.value = false

      // Restore original window title
      document.title = originalWindowTitle.value

      loadImages()
    })

    // Handle error
    ipcRenderer.once('preset-to-batch-error', (_, result) => {
      console.error('Error saving all files:', result.message, result.error)
      isSavingAll.value = false

      // Restore original window title
      document.title = originalWindowTitle.value
    })
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

  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer

    // Check if working directory was provided by PhotoDirectory
    if (route.query.workingDirectory) {
      // Use the provided working directory directly
      workingDirectory.value = route.query.workingDirectory
      originalDirectoryPath.value = route.query.originalDirectory || ''
      compressPreview.value = route.query.compressPreview === '1'
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
      compressPreview.value = route.query.compressPreview === '1'
      ipcRenderer.send('prepare-working-directory', directoryPath.value, { compressPreview: compressPreview.value })

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
  background: var(--bg-page);
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
  background: var(--bg-surface);
  border-radius: 8px;
  box-shadow: 0 2px 4px var(--shadow);
}

.back-button {
  padding: 10px 20px;
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s ease;
}

.back-button:hover {
  background: var(--accent-hover);
}

.refresh-button {
  padding: 10px 20px;
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s ease;
  margin-right: 10px;
}

.refresh-button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.refresh-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-title {
  font-size: 24px;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
  text-align: center;
}

.count-badge {
  padding: 6px 12px;
  background: var(--accent);
  color: var(--text-on-accent);
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
  color: var(--text-secondary);
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid var(--border-light);
  border-top: 4px solid var(--accent);
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
  color: var(--text-primary);
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 16px;
  color: var(--text-secondary);
  max-width: 400px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 20px;
}

.image-item {
  background: var(--bg-surface);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  box-shadow: 0 2px 4px var(--shadow);
}

.image-item:hover:not(.applying) {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px var(--shadow);
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
  color: var(--text-primary);
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
  color: var(--text-on-accent);
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
  color: var(--text-on-accent);
  text-align: center;
  font-size: 14px;
}
</style>
