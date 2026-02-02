<template>
  <div class="app">
    <router-view />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme } from './composables/useTheme'
import Toast from './components/Toast.vue'

const { initTheme } = useTheme()

onMounted(() => {
  initTheme()
})
</script>

<style>
/* Global styles */
* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
}

#app {
  height: 100%;
}

.app {
  min-height: 100%;
}
</style>
