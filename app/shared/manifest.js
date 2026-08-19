// Working-directory manifest — the "inventory" that lets the renderer know the
// full list of images (including ones not yet copied/resized), kept separate
// from "which files are actually on disk" (ready). See design/early-use.md.
//
// Ready-ness is never stored here: a file is "ready" iff it exists on disk in
// the working directory. This file only answers "what are ALL the names", so
// `get-images` can render placeholders for the not-yet-ready remainder.
const fs = require('fs')
const path = require('path')

const MANIFEST_FILENAME = '.manifest.json'
const ERRORS_FILENAME = '.errors.json'

// Write the full inventory once, at job start. `files` = [{ name, isRaw }].
function writeManifest(workingDirectory, files) {
  const data = { total: files.length, files }
  fs.writeFileSync(path.join(workingDirectory, MANIFEST_FILENAME), JSON.stringify(data))
}

// Parsed manifest, or null when absent (legacy working dirs with no early-use).
function readManifest(workingDirectory) {
  const p = path.join(workingDirectory, MANIFEST_FILENAME)
  if (!fs.existsSync(p)) return null
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'))
  } catch (err) {
    return null
  }
}

// Record a per-file failure. Rare (only on resize/copy errors), so rewriting the
// whole errors object each time is fine.
function recordError(workingDirectory, name, error) {
  const p = path.join(workingDirectory, ERRORS_FILENAME)
  let errors = {}
  if (fs.existsSync(p)) {
    try { errors = JSON.parse(fs.readFileSync(p, 'utf-8')) } catch (_) { errors = {} }
  }
  errors[name] = error
  fs.writeFileSync(p, JSON.stringify(errors))
}

// { [name]: error } — empty when no failures recorded.
function readErrors(workingDirectory) {
  const p = path.join(workingDirectory, ERRORS_FILENAME)
  if (!fs.existsSync(p)) return {}
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'))
  } catch (err) {
    return {}
  }
}

module.exports = {
  MANIFEST_FILENAME,
  ERRORS_FILENAME,
  writeManifest,
  readManifest,
  recordError,
  readErrors
}
