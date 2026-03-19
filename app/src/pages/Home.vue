<template>
  <div class="home-page">
    <header class="header">
      <h1>OpenLucky Desktop</h1>
      <p>An opensourced, light-weighted negative film process tool.</p>

    </header>

    <main class="main-content">
      <div class="feature-grid">
        <FeatureCard
          v-for="feature in features"
          :key="feature.id"
          :title="feature.title"
          :description="feature.description"
          :icon="feature.icon"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FeatureCard from '../components/FeatureCard.vue'

const features = ref([
  {
    id: 1,
    title: 'Film Processing',
    description: 'Process and manage your negative film batches efficiently',
    icon: '🎞️'
  },
  {
    id: 2,
    title: 'Common Tools',
    description: 'Quick access to everyday utility tools',
    icon: '🧰'
  },
  {
    id: 3,
    title: 'Configuration',
    description: 'Customize your workflow with flexible settings',
    icon: '⚙️'
  },
  {
    id: 4,
    title: 'Analytics',
    description: 'Track your progress with detailed analytics',
    icon: '📊'
  }
])
</script>

<style scoped>
.home-page {
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 40px;
}

.header h1 {
  font-size: 32px;
  color: #42b883;
  margin-bottom: 10px;
}

.header p {
  font-size: 16px;
  color: #666;
}

/* 🔴 临时调试样式 - 调试完成后删除 */
.debug-info {
  font-size: 12px;
  color: #888;
  margin-top: 5px;
  font-family: monospace;
}
/* 🔴 临时调试样式结束 */

.main-content {
  max-width: 1200px;
  margin: 0 auto;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}
</style>
