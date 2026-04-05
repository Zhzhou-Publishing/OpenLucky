<template>
  <div class="about-page">
    <h1>{{ $t('about.title') }}</h1>
    <div class="content">
      <section class="info-section">
        <h2>{{ $t('about.version') }}</h2>
        <p>OpenLucky Desktop {{ version }}</p>
      </section>

      <section class="info-section">
        <h2>{{ $t('about.description') }}</h2>
        <p>{{ $t('about.descriptionText') }}</p>
      </section>

      <section class="info-section">
        <h2>{{ $t('about.technologies') }}</h2>
        <ul class="tech-list">
          <li v-for="tech in technologies" :key="tech">{{ tech }}</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const version = ref(__APP_VERSION__)
const technologies = ref([
  'Electron',
  'Vue 3',
  'Vue Router',
  'Vite',
  'JavaScript'
])
</script>

<style scoped>
.about-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  color: #42b883;
  margin-bottom: 30px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.info-section h2 {
  font-size: 18px;
  color: #35495e;
  margin-bottom: 10px;
}

.info-section p {
  line-height: 1.6;
  color: #666;
}

.tech-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tech-list li {
  background: #f5f5f5;
  padding: 5px 15px;
  border-radius: 4px;
  font-size: 14px;
  color: #42b883;
}
</style>
