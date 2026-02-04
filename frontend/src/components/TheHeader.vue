<template>
  <header class="app-header">
    <div class="container">
      <div class="logo-wrapper">
        <div class="logo-icon">PD</div>
        <h1 class="logo">PilotDeck</h1>
      </div>
      
      <div class="header-actions">
        <button 
          class="btn-icon theme-toggle" 
          @click="toggleTheme" 
          :title="`切换${currentTheme === 'dark' ? '浅色' : '深色'}主题`"
        >
          <svg v-if="currentTheme === 'light'" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
          <svg v-else class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </button>
        
        <div class="divider"></div>
        
        <button class="btn btn-ghost" @click="$emit('show-stats')">
          统计信息
        </button>
        
        <button class="btn btn-ghost" @click="$emit('show-ops')">
          运维
        </button>
        
        <button class="btn btn-primary" @click="$emit('add-project')">
          <svg class="btn-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          添加项目
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useTheme } from '../composables/useTheme'

const { currentTheme, toggleTheme } = useTheme()

defineEmits<{
  'show-stats': []
  'show-ops': []
  'add-project': []
}>()
</script>

<style scoped>
.app-header {
  background: var(--header-bg);
  backdrop-filter: var(--backdrop-blur);
  -webkit-backdrop-filter: var(--backdrop-blur);
  border-bottom: 1px solid var(--header-border);
  padding: 16px 0;
  position: sticky;
  top: 0;
  z-index: 50;
  transition: background 0.3s, border-color 0.3s;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-600));
  border-radius: 8px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.logo {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
  margin: 0 4px;
}

.btn-icon {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: var(--bg-color);
  color: var(--text-primary);
  border-color: var(--primary-color);
}

.icon {
  width: 20px;
  height: 20px;
}

.btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.btn-primary:hover {
  background: var(--primary-hover);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.btn-icon-svg {
  width: 16px;
  height: 16px;
}
</style>
