// Pure, dependency-free version / update-channel / recall logic.
//
// Extracted from main.js so the (security- and UX-critical) update and recall
// rules can be unit-tested without electron, and so the Tauri/Rust port can
// reproduce them exactly. main.js wires these to electron's `app`/`https`/`fs`.

// Tumbleweed channels: a release only nudges users on the same channel.
// 'stable' (no suffix) → next stable
// 'rc' / 'beta' / 'alpha' → next release in the same channel
function getVersionChannel(version) {
  if (!version) return 'stable'
  const v = String(version).toLowerCase()
  if (/-rc/i.test(v)) return 'rc'
  if (/-beta/i.test(v)) return 'beta'
  if (/-alpha/i.test(v)) return 'alpha'
  return 'stable'
}

// Normalize a raw version string to the tag form used for comparison/lookups:
// ensure a leading 'v'. Empty/falsy input is returned unchanged.
function normalizeVersion(version) {
  if (!version) return version
  return version.startsWith('v') ? version : 'v' + version
}

// Interpret the contents of the lastUpdateCheck storage file.
// The file holds either a timestamp (normal) or "recall:<version>" marker.
// Returns { recalled: boolean, version?: string }. A recall only applies when
// the recalled version matches the currently running version.
function parseRecallData(data, currentVersion) {
  if (typeof data !== 'string') return { recalled: false }
  const trimmed = data.trim()
  if (!trimmed.startsWith('recall:')) {
    return { recalled: false }
  }
  const recalledVersion = trimmed.substring('recall:'.length)
  if (recalledVersion === currentVersion) {
    return { recalled: true, version: recalledVersion }
  }
  return { recalled: false }
}

// Whether a locale string denotes Simplified Chinese (used to localize dialogs).
function isChineseLocale(locale) {
  const l = String(locale || '').toLowerCase()
  return l === 'zh_cn' || l === 'zh-cn' || l === 'zh-hans' || l === 'zh_hans'
}

// Hour-bucketed update throttle: check at most once per wall-clock hour.
// lastCheck === 0 (never checked) → always check.
function shouldCheckByHour(lastCheck, now) {
  if (!lastCheck) return true
  const lastCheckHour = Math.floor(lastCheck / (60 * 60 * 1000))
  const currentHour = Math.floor(now / (60 * 60 * 1000))
  return currentHour > lastCheckHour
}

module.exports = {
  getVersionChannel,
  normalizeVersion,
  parseRecallData,
  isChineseLocale,
  shouldCheckByHour
}
