/**
 * Global state management for the application
 */
import { reactive } from 'vue'
import { createRendererLogger } from './rendererLogger'

const logger = createRendererLogger('GlobalState')

export const globalState = reactive({
  isSaveAllClicked: false
})

export function setSaveAllClicked(value) {
  logger.debug('Global state isSaveAllClicked changed:', globalState.isSaveAllClicked, '->', value)
  globalState.isSaveAllClicked = value
}

export function getSaveAllClicked() {
  return globalState.isSaveAllClicked
}
