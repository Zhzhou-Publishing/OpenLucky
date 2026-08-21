import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { initJobProgress } from './utils/jobProgress'

// Subscribe once to the directory-load progress stream so the window title and
// any button keep showing `[N/M] <path>` on every page until loading completes.
initJobProgress()

const app = createApp(App)
app.use(router)
app.use(i18n)
app.mount('#app')
