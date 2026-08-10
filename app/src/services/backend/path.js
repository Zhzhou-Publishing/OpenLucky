// Pure-JS path helpers for the renderer.
//
// The renderer currently pulls `path` from Electron's Node via
// `window.require('path')`, which is unavailable in a Tauri bundle. These are the
// only path operations the renderer uses today (path.join / path.basename /
// path.extname), reimplemented without Node so they work on both backends.
// This is NOT a full node:path polyfill — only what the UI needs.

const SEP = typeof navigator !== 'undefined' && navigator.userAgent && navigator.userAgent.includes('Windows') ? '\\' : '/'

export function join(...parts) {
  const p = parts.filter(x => typeof x === 'string' && x.length > 0)
  if (p.length === 0) return ''
  const joined = p.join(SEP)
  // collapse duplicate separators
  return joined.replace(/([\\/])+/g, (m, sep) => sep)
}

export function basename(p) {
  if (typeof p !== 'string' || p.length === 0) return ''
  const t = p.replace(/[\\/]+$/, '')
  const i = Math.max(t.lastIndexOf('/'), t.lastIndexOf('\\'))
  return i === -1 ? t : t.slice(i + 1)
}

export function extname(p) {
  if (typeof p !== 'string' || p.length === 0) return ''
  const base = basename(p)
  const dot = base.lastIndexOf('.')
  // no dot, or dot at start (hidden file) or end -> empty extension
  if (dot <= 0) return ''
  return base.slice(dot)
}

export const path = { join, basename, extname }
