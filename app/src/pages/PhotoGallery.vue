<template>
  <div class="photo-gallery-page">
    <div class="header">
      <button @click="goBack" class="back-button">← Back</button>
      <h1 class="page-title">{{ title }}</h1>
      <button @click="loadImages" class="refresh-button" :disabled="isLoading">
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
      <p>No image files (jpg, jpeg, png, gif, webp, tiff) were found in the selected directory.</p>
    </div>

    <div v-else class="gallery-grid">
      <div v-for="(image, index) in images" :key="index" class="image-item" @contextmenu.prevent="openImage(image)">
        <img :src="image.url" :alt="image.name" class="thumbnail" loading="lazy" />
        <div class="image-info">
          <p class="image-name">{{ image.name }}</p>
        </div>
      </div>
    </div>

    <!-- Bottom Menu Bar -->
    <div v-if="!isLoading && images.length > 0" class="bottom-menu">
      <div class="menu-item">
        <label class="menu-label">Preset:</label>
        <select v-model="selectedPreset" class="preset-select" :disabled="isLoading || isApplyingPreset">
          <option v-for="preset in presets" :key="preset.value" :value="preset.value">
            {{ preset.label }}
          </option>
        </select>
        <button @click="applyPreset" class="apply-button" :disabled="isLoading || isApplyingPreset">
          {{ applyButtonText }}
          <span v-if="hasUnappliedChanges" class="red-dot"></span>
        </button>
      </div>
    </div>

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

const router = useRouter()
const route = useRoute()

const images = ref([])
const isLoading = ref(true)
const selectedImage = ref(null)
const selectedPreset = ref('lucky_c200_2025')
const hasUnappliedChanges = ref(true)
const isApplyingPreset = ref(false)
const previewingDirectory = ref('')
const workingDirectory = ref('')

const applyButtonText = computed(() => {
  return isApplyingPreset.value ? 'Applying...' : 'Apply'
})

const presets = [
  { value: 'lucky_c200_2025', label: 'Lucky C200 (2025)' },
  { value: 'fujifilm_c200', label: 'Fujifilm C200' },
  { value: 'fujifilm_c400', label: 'Fujifilm C400' },
  { value: 'kodak_colorplus_200', label: 'Kodak ColorPlus 200 (Kodak Alaris)' },
  { value: 'kodak_gold_200', label: 'Kodak Gold 200 (Kodak Alaris)' },
  { value: 'kodak_ultramax_400', label: 'Kodak Ultramax 400 (Kodak Alaris)' }
]

const directoryPath = computed(() => route.query.path || '')

const title = computed(() => {
  if (directoryPath.value) {
    const parts = directoryPath.value.split(/[/\\]/)
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

        // Wait a moment for the output directory to be created
        await new Promise(resolve => setTimeout(resolve, 1000))

        // Update previewingDirectory to output subdirectory and refresh
        const path = window.require('path')
        const outputPath = path.join(directoryPath.value, 'output')
        previewingDirectory.value = outputPath
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
    if (!previewingDirectory.value) {
      router.push('/photo-directory')
      return
    }

    // Check if running in Electron
    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      // Request images from main process
      ipcRenderer.send('get-images', previewingDirectory.value)

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

onMounted(() => {
  previewingDirectory.value = directoryPath.value
  workingDirectory.value = directoryPath.value
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

.bottom-menu {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #e0e0e0;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  padding: 16px 20px;
  display: flex;
  justify-content: center;
  z-index: 100;
  animation: slideUp 1s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(100%);
    opacity: 0;
  }

  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-label {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.preset-select {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
  background: white;
  cursor: pointer;
  transition: border-color 0.2s ease;
  min-width: 180px;
}

.preset-select:hover {
  border-color: #42b883;
}

.preset-select:focus {
  outline: none;
  border-color: #42b883;
  box-shadow: 0 0 0 3px rgba(66, 184, 131, 0.1);
}

.preset-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.apply-button {
  padding: 8px 16px;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, opacity 0.2s ease;
  position: relative;
  margin-left: 10px;
  min-width: 120px;
}

.apply-button:hover:not(:disabled) {
  background: #35a372;
}

.apply-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.red-dot {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 12px;
  height: 12px;
  background: #ff4444;
  border-radius: 50%;
  border: 2px solid white;
}
</style>
