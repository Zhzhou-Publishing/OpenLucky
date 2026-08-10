// Backend facade entry — the single swap point for the renderer.
//
// At this stage ONLY the Electron backend is implemented. When the Tauri/Rust
// backend is built, add tauri.js next to electron.js and flip the selection
// here (e.g. via a __BACKEND__ Vite define). Pages import from this module and
// never touch window.require('electron') directly.

import * as electronBackend from './electron'

const backend = electronBackend

export default backend
export { backend }

// Re-export path so pages can `import { path } from '../services/backend'`.
export const path = backend.path
