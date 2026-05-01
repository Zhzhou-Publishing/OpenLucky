<template>
  <div id="app">
    <Navbar />
    <main class="main-container">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Navbar from './components/Navbar.vue'
import twemoji from '@twemoji/api'
import { globalState } from './utils/globalState'
import './utils/theme' // 初始化主题系统（读 localStorage → 设置 dark class）

const route = useRoute()
const { t } = useI18n()

// Routes that hold loaded image state; closing the window from here
// without a SaveAll loses the unsaved work.
const PROTECTED_PATHS = ['/photo-gallery', '/photo-edit']

let observer = null
let ipcRenderer = null
const onConfirmClose = () => {
  const guarded = PROTECTED_PATHS.includes(route.path) && !globalState.isSaveAllClicked
  if (!guarded || window.confirm(t('navbar.closeConfirm'))) {
    ipcRenderer.send('confirm-close-response', true)
  }
}

const twemojiConfig = {
  base: './',
  folder: './build-resources/emoji',
  ext: '.svg',
  className: 'twemoji'
}

const parseTwemoji = () => {
  twemoji.parse(document.body, twemojiConfig)
}

onMounted(() => {
  if (window.require) {
    ipcRenderer = window.require('electron').ipcRenderer
    ipcRenderer.on('confirm-close', onConfirmClose)
  }

  // 初始化 Twemoji
  parseTwemoji()

  // 监听 DOM 变化以重新解析 emoji
  observer = new MutationObserver(() => {
    parseTwemoji()
  })

  // 观察整个 body 的变化
  observer.observe(document.body, {
    childList: true,
    subtree: true
  })
})

onUnmounted(() => {
  // 清理观察者
  if (observer) {
    observer.disconnect()
  }
  if (ipcRenderer) {
    ipcRenderer.removeListener('confirm-close', onConfirmClose)
  }
})
</script>

<style>
@import '@fontsource/noto-sans-sc/400.css';
@import '@fontsource/noto-sans-sc/500.css';
@import '@fontsource/noto-sans-sc/600.css';

:root {
  /* 浅色主题（默认） */
  --bg-page: #f5f5f5;
  --bg-surface: #ffffff;
  --bg-surface-hover: #f0f0f0;
  --bg-input: #ffffff;
  --text-primary: #333333;
  --text-secondary: #666666;
  --text-tertiary: #999999;
  --text-on-accent: #ffffff;
  --border-color: #e0e0e0;
  --border-light: #dddddd;
  --accent: #42b883;
  --accent-hover: #35a372;
  --btn-save-bg: #42a5f5;
  --btn-save-hover: #2196f3;
  --btn-save-disabled: #90caf9;
  --btn-disabled-bg: #cccccc;
  --btn-disabled-text: #999999;
  --danger: #ff4444;
  --shadow: rgba(0, 0, 0, 0.1);
}

:root.dark {
  /* 深色主题 */
  --bg-page: #323232;
  --bg-surface: #3c3c3c;
  --bg-surface-hover: #4a4a4a;
  --bg-input: #3c3c3c;
  --text-primary: #bdbdbd;
  --text-secondary: #888888;
  --text-tertiary: #666666;
  --text-on-accent: #ffffff;
  --border-color: #4a4a4a;
  --border-light: #3c3c3c;
  --accent: #42b883;
  --accent-hover: #35a372;
  --btn-save-bg: #42a5f5;
  --btn-save-hover: #2196f3;
  --btn-save-disabled: #555555;
  --btn-disabled-bg: #555555;
  --btn-disabled-text: #888888;
  --danger: #ff4444;
  --shadow: rgba(0, 0, 0, 0.3);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg-page);
  color: var(--text-primary);
  overflow: hidden;
}

/* Twemoji styles */
.twemoji {
  display: inline-block;
  vertical-align: middle;
  width: 1em;
  height: 1em;
  margin: 0 0.05em;
}

#app {
  min-height: 100vh;
}

.main-container {
  background: var(--bg-page);
  height: calc(100vh - 64px);
  overflow: hidden;
}

/* Hide scrollbar for Chrome, Safari and Opera */
::-webkit-scrollbar {
  display: none;
}

/* Hide scrollbar for IE, Edge and Firefox */
html, body, * {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
</style>
