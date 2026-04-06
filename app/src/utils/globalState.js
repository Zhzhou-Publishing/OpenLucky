/**
 * Global state management for the application
 */

export const globalState = {
  isSaveAllClicked: false
}

export function setSaveAllClicked(value) {
  globalState.isSaveAllClicked = value
}

export function getSaveAllClicked() {
  return globalState.isSaveAllClicked
}
