// Preset 全局缓存模块

// 内存缓存
let cache = {
  presets: null,
  timestamp: null
}

// 缓存有效期（5分钟）
const CACHE_DURATION = 5 * 60 * 1000

/**
 * 获取缓存的预设列表
 * @returns {Array|null} 缓存的预设列表，如果不存在或已过期则返回 null
 */
export function getCachedPresets() {
  if (!cache.presets || !cache.timestamp) {
    return null
  }

  const now = Date.now()
  if (now - cache.timestamp > CACHE_DURATION) {
    // 缓存已过期
    cache.presets = null
    cache.timestamp = null
    return null
  }

  return cache.presets
}

/**
 * 更新缓存
 * @param {Array} presets - 预设列表
 */
export function updateCachedPresets(presets) {
  cache.presets = presets
  cache.timestamp = Date.now()
}

/**
 * 清除缓存
 */
export function clearCachedPresets() {
  cache.presets = null
  cache.timestamp = null
}

/**
 * 检查缓存是否存在且有效
 * @returns {boolean} 缓存是否有效
 */
export function hasValidCache() {
  return getCachedPresets() !== null
}
