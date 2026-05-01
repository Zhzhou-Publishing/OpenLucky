<template>
  <div class="tabs-example">
    <h2>Tab Component Example</h2>
    <Tabs
      :tabs="tabs"
      default-tab="home"
      @tab-change="handleTabChange"
    >
      <template #default="{ activeTab }">
        <div v-if="activeTab === 'home'" class="tab-content">
          <h3>Home Tab</h3>
          <p>This is the home tab content.</p>
        </div>
        <div v-if="activeTab === 'profile'" class="tab-content">
          <h3>Profile Tab</h3>
          <p>This is the profile tab content.</p>
        </div>
        <div v-if="activeTab === 'settings'" class="tab-content">
          <h3>Settings Tab</h3>
          <p>This is the settings tab content.</p>
        </div>
      </template>
    </Tabs>
  </div>
</template>

<script setup>
import Tabs from './Tabs.vue'
import { ref } from 'vue'

const tabs = ref([
  { id: 'home', label: 'Home' },
  { id: 'profile', label: 'Profile' },
  { id: 'settings', label: 'Settings' }
])

const handleTabChange = (tabId) => {
  console.log('Tab changed to:', tabId)
}
</script>

<style scoped>
.tabs-example {
  padding: 20px;
  max-width: 800px;
}

.tabs-example h2 {
  color: var(--text-primary);
  margin-bottom: 20px;
}

.tab-content {
  padding: 20px;
  background: var(--bg-surface);
  border-radius: 8px;
  box-shadow: 0 2px 4px var(--shadow);
}

.tab-content h3 {
  color: var(--accent);
  margin-top: 0;
}

.tab-content p {
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
