import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'

// 读取 package.json 获取版本号
const packageJson = JSON.parse(readFileSync('./package.json', 'utf-8'))
const version = packageJson.version

export default defineConfig({
  base: './',
  plugins: [vue()],
  build: {
    outDir: 'dist',
    // 确保复制 build-resources 到 dist
    copyPublicDir: true
  },
  define: {
    __APP_VERSION__: JSON.stringify(version)
  }
})
