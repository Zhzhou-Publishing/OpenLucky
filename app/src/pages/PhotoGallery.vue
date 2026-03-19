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
      <p>No image files (jpg, jpeg, png, gif, webp) were found in the selected directory.</p>
    </div>

    <div v-else class="gallery-grid">
      <div
        v-for="(image, index) in images"
        :key="index"
        class="image-item"
        @click="openImage(image)"
      >
        <img :src="image.url" :alt="image.name" class="thumbnail" loading="lazy" />
        <div class="image-info">
          <p class="image-name">{{ image.name }}</p>
        </div>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const images = ref([])
const isLoading = ref(true)
const selectedImage = ref(null)

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

const loadImages = async () => {
  try {
    isLoading.value = true

    if (!directoryPath.value) {
      router.push('/photo-directory')
      return
    }

    // Check if running in Electron
    if (window.require) {
      const ipcRenderer = window.require('electron').ipcRenderer

      // Request images from main process
      ipcRenderer.send('get-images', directoryPath.value)

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
  loadImages()
})
</script>

<style scoped>
.photo-gallery-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20px;
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
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
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
  height: 200px;
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
  from { opacity: 0; }
  to { opacity: 1; }
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
