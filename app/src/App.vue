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
import Navbar from './components/Navbar.vue'
import twemoji from '@twemoji/api'

let observer = null

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
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
