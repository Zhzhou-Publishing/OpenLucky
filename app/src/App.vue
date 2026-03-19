<template>
  <div id="app">
    <Navbar />
    <main class="main-container">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Navbar from './components/Navbar.vue'
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
