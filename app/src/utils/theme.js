import { ref } from 'vue'

const THEME_KEY = 'openlucky-theme'
const theme = ref(localStorage.getItem(THEME_KEY) || 'dark')

function applyTheme(name) {
  theme.value = name
  localStorage.setItem(THEME_KEY, name)
  document.documentElement.classList.toggle('dark', name === 'dark')
}

// 初始化：页面加载时应用已保存的主题
applyTheme(theme.value)

export function useTheme() {
  return { theme, setTheme: applyTheme }
}
