<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <span class="brand-icon">📷</span>
      <span class="brand-name">OpenLucky</span>
    </div>
    <div class="navbar-menu">
      <a
        v-for="r in routes"
        :key="r.path"
        href="#"
        class="nav-link"
        :class="{ active: currentPath === r.path }"
        @click.prevent="navigate(r.path)"
      >
        {{ $t(r.i18nKey) }}
      </a>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const routes = [
  { path: '/', i18nKey: 'navbar.home' },
  { path: '/about', i18nKey: 'navbar.about' }
]

// Routes that hold loaded image state and warrant a confirmation when leaving.
const PROTECTED_PATHS = ['/photo-gallery', '/photo-edit']

const currentPath = computed(() => route.path)

function navigate(target) {
  if (currentPath.value === target) return
  if (PROTECTED_PATHS.includes(currentPath.value)) {
    if (!window.confirm(t('navbar.leaveConfirm'))) return
  }
  router.push(target)
}
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-surface);
  box-shadow: 0 2px 4px var(--shadow);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  color: var(--accent);
}

.brand-icon {
  font-size: 24px;
}

.navbar-menu {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  text-decoration: none;
  color: var(--text-secondary);
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s;
  cursor: pointer;
}

.nav-link:hover {
  background: var(--bg-surface-hover);
  color: var(--accent);
}

.nav-link.active {
  background: var(--accent);
  color: var(--text-on-accent);
}
</style>
