import { ref } from 'vue'
import { createRendererLogger } from './rendererLogger'

const logger = createRendererLogger('PresetCache')

export const presets = ref([])

/** 全局色罩临时预设：吸取一次色罩供整卷使用，同一次 app 会话内跨页面保持 */
export const globalMaskPreset = ref(null)

export function fetchPresets() {
  return new Promise((resolve, reject) => {
    if (!window.require) {
      resolve(presets.value)
      return
    }
    try {
      const ipcRenderer = window.require('electron').ipcRenderer
      const onLoaded = (_, result) => {
        ipcRenderer.removeListener('presets-error', onError)
        presets.value = result.presets || []
        resolve(presets.value)
      }
      const onError = (_, error) => {
        ipcRenderer.removeListener('presets-loaded', onLoaded)
        logger.error('Error loading presets:', error)
        reject(error)
      }
      ipcRenderer.once('presets-loaded', onLoaded)
      ipcRenderer.once('presets-error', onError)
      ipcRenderer.send('get-presets')
    } catch (error) {
      logger.error('Error loading presets:', error)
      reject(error)
    }
  })
}
