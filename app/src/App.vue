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

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f5f5;
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
  background: #f5f5f5;
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
