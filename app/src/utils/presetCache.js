import { ref } from 'vue'

export const presets = ref([])

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
        console.error('Error loading presets:', error)
        reject(error)
      }
      ipcRenderer.once('presets-loaded', onLoaded)
      ipcRenderer.once('presets-error', onError)
      ipcRenderer.send('get-presets')
    } catch (error) {
      console.error('Error loading presets:', error)
      reject(error)
    }
  })
}
