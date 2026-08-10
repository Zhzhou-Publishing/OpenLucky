import { ref } from 'vue'
import { createRendererLogger } from './rendererLogger'
import backend from '../services/backend'

const logger = createRendererLogger('PresetCache')

export const presets = ref([])

/** 全局色罩临时预设：吸取一次色罩供整卷使用，同一次 app 会话内跨页面保持 */
export const globalMaskPreset = ref(null)

export function fetchPresets() {
  if (!backend.isAvailable()) {
    return Promise.resolve(presets.value)
  }
  return backend.getPresets()
    .then((result) => {
      presets.value = result.presets || []
      return presets.value
    })
    .catch((error) => {
      logger.error('Error loading presets:', error)
      throw error
    })
}
