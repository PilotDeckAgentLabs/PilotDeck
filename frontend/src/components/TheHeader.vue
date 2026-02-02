<template>
  <header class="app-header">
    <div class="container">
      <h1 class="logo">我的项目管理系统</h1>
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
        
        <button class="btn btn-secondary" @click="$emit('show-stats')">
          统计信息
        </button>
        
        <button class="btn btn-secondary" @click="$emit('show-ops')">
          运维
        </button>
        
        <button class="btn btn-primary" @click="$emit('add-project')">
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
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(37, 99, 235, 0.85));
  color: white;
  padding: 18px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.25);
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
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-primary {
  background: white;
  color: var(--primary-color);
}

.btn-primary:hover {
  background: rgba(255, 255, 255, 0.9);
}
</style>
