import { ref } from 'vue'
import backend from '../services/backend'

const THEME_KEY = 'openlucky-theme'
const theme = ref(localStorage.getItem(THEME_KEY) || 'dark')

function applyTheme(name) {
  theme.value = name
  localStorage.setItem(THEME_KEY, name)
  document.documentElement.classList.toggle('dark', name === 'dark')
  if (backend.isAvailable()) {
    try {
      backend.setTheme(name)
    } catch (_) { /* not in Electron */ }
  }
}

// 初始化：页面加载时应用已保存的主题
applyTheme(theme.value)

export function useTheme() {
  return { theme, setTheme: applyTheme }
}
