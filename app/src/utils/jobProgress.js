// Persistent directory-load progress, shared across pages.
//
// The prepare job (prepare-working-directory-from-selected) streams
// `processing-progress-update` for the WHOLE load — not just until the 1/3
// partial-ready gate — so any page can keep the window title and a button in
// sync with `[N/M] <source path>` until every image is done. This module is the
// single subscriber; pages read the `jobProgress` ref and never re-subscribe.

import { ref } from 'vue'
import { createRendererLogger } from './rendererLogger'
import backend from '../services/backend'

const logger = createRendererLogger('JobProgress')

export const BASE_TITLE = 'OpenLucky Desktop App'

/** `[N/M] <filename>` while a directory load is running, '' otherwise. */
export const jobProgress = ref('')

/** Full source path of the file currently being processed ('' when idle). */
export const jobPath = ref('')

// The title shown before the load started (may be localized by the current
// page); restored when the load finishes so we never clobber it with English.
let preLoadTitle = BASE_TITLE

let initialized = false

/** Re-apply the window title: load progress if active, else the pre-load title. */
export function refreshTitle() {
  document.title = jobProgress.value ? jobProgress.value : preLoadTitle
}

/** Subscribe once (renderer startup); safe to call on any page / repeatedly. */
export function initJobProgress() {
  if (initialized) return
  initialized = true
  if (!backend.isAvailable()) {
    logger.debug('Job progress inactive: Electron IPC unavailable')
    return
  }
  backend.onJobProgress((_e, payload) => {
    const { progress, path } = payload || {}
    // First progress tick: capture the page's current (possibly localized) title
    // so we can restore it once the whole load is done.
    if (!jobProgress.value) preLoadTitle = document.title
    jobProgress.value = progress
    jobPath.value = path || ''
    refreshTitle()
  })
  backend.onJobProgressClear(() => {
    jobProgress.value = ''
    jobPath.value = ''
    refreshTitle()
  })
  logger.debug('Job progress stream subscribed')
}
