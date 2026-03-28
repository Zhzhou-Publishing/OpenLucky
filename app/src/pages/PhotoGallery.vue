<template>
  <div class="photo-gallery-page">
    <div class="header">
      <button @click="goBack" class="back-button">← Back</button>
      <h1 class="page-title">{{ title }}</h1>
      <button @click="handleRefresh" class="refresh-button" :disabled="isLoading">
        🔄 Refresh
      </button>
      <span class="count-badge">{{ images.length }} images</span>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading images...</p>
    </div>

    <div v-else-if="images.length === 0" class="empty-state">
      <p class="empty-icon">📷</p>
      <h2>No Images Found</h2>
      <p>No image files (jpg, jpeg, png, gif, webp, tiff, arw, cr2, cr3, nef, dng, orf, raf) were found in the selected directory.</p>
    </div>

    <div v-else class="gallery-grid">
      <div v-for="(image, index) in images" :key="index" class="image-item" @click="openPhotoEdit(image)" @contextmenu.prevent="openImage(image)">
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
      :images-count="images.length"
      @update:selected-preset="selectedPreset = $event"
      @apply="applyPreset"
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
import BottomMenuBar from '../components/BottomMenuBar.vue'

const router = useRouter()
const route = useRoute()

const images = ref([])
const isLoading = ref(true)
const selectedImage = ref(null)
const selectedPreset = ref('lucky_c200_2025')
const hasUnappliedChanges = ref(true)
const isApplyingPreset = ref(false)
const workingDirectory = ref('')

const directoryPath = computed(() => route.query.path || '')

const title = computed(() => {
  if (workingDirectory.value) {
    const parts = workingDirectory.value.split(/[/\\]/)
    return parts[parts.length - 1] || 'Photo Gallery'
  }
  return 'Photo Gallery'
})

const goBack = () => {
  router.push('/photo-directory')
}

const openImage = (image) => {
  selectedImage.value = image
}

const openPhotoEdit = (image) => {
  router.push({
    path: '/photo-edit',
    query: {
      workingDirectory: workingDirectory.value,
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
      })

      // Send request to main process
      ipcRenderer.send('apply-preset', {
        directoryPath: workingDirectory.value,
        preset: selectedPreset.value
      })
    } else {
      // Fallback for non-Electron environment
      console.warn('Not running in Electron, cannot apply preset')
      isApplyingPreset.value = false
    }
  } catch (error) {
    console.error('Error applying preset:', error)
    isApplyingPreset.value = false
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

        // Check for RAW files that are still converting
        const convertingRawFiles = result.images.filter(img => img.isRaw && !img.converted)
        if (convertingRawFiles.length > 0) {
          startRawConversionMonitoring()
        }
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

let rawConversionMonitorInterval = null

const startRawConversionMonitoring = () => {
  if (rawConversionMonitorInterval) {
    clearInterval(rawConversionMonitorInterval)
  }

  rawConversionMonitorInterval = setInterval(() => {
    if (!window.require) return

    const ipcRenderer = window.require('electron').ipcRenderer

    ipcRenderer.send('get-images', workingDirectory.value)

    ipcRenderer.once('images-loaded', (_, result) => {
      const hasUnconvertedRaw = result.images.some(img => img.isRaw && !img.converted)
      images.value = result.images

      // Stop monitoring if all RAW files are converted
      if (!hasUnconvertedRaw && rawConversionMonitorInterval) {
        clearInterval(rawConversionMonitorInterval)
        rawConversionMonitorInterval = null
      }
    })
  }, 2000) // Check every 2 seconds
}

const stopRawConversionMonitoring = () => {
  if (rawConversionMonitorInterval) {
    clearInterval(rawConversionMonitorInterval)
    rawConversionMonitorInterval = null
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

onMounted(() => {
  workingDirectory.value = directoryPath.value
  // Load images
  loadImages()
  // Make window resizable when entering photo gallery
  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.send('set-window-resizable', true)
  }
})

onUnmounted(() => {
  // Make window non-resizable when leaving photo gallery
  if (window.require) {
    const ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.send('set-window-resizable', false)
  }
  // Stop RAW conversion monitoring
  stopRawConversionMonitoring()
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

.image-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
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
