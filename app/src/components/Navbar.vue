<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <span class="brand-icon">📷</span>
      <span class="brand-name">OpenLucky</span>
    </div>
    <div class="navbar-menu">
      <router-link
        v-for="route in routes"
        :key="route.path"
        :to="route.path"
        class="nav-link"
        active-class="active"
      >
        {{ route.name }}
      </router-link>
    </div>
  </nav>
</template>

<script setup>
const routes = [
  { path: '/', name: 'PhotoDirectory' },
  { path: '/about', name: 'About' }
]
</script>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
  color: #42b883;
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
  color: #666;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #f5f5f5;
  color: #42b883;
}

.nav-link.active {
  background: #42b883;
  color: white;
}
</style>
