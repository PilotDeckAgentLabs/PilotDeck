<template>
  <div class="filters">
    <div class="filter-group">
      <label for="status-filter">状态筛选：</label>
      <select 
        id="status-filter"
        :value="filters.status"
        @change="onFilterChange('status', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">全部状态</option>
        <option value="planning">计划中</option>
        <option value="in-progress">进行中</option>
        <option value="paused">暂停</option>
        <option value="completed">已完成</option>
        <option value="cancelled">已取消</option>
      </select>
    </div>

    <div class="filter-group">
      <label for="priority-filter">优先级筛选：</label>
      <select 
        id="priority-filter"
        :value="filters.priority"
        @change="onFilterChange('priority', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">全部优先级</option>
        <option value="low">低</option>
        <option value="medium">中</option>
        <option value="high">高</option>
        <option value="urgent">紧急</option>
      </select>
    </div>

    <div class="filter-group">
      <label for="sort-mode">排序：</label>
      <select 
        id="sort-mode"
        :value="sortMode"
        @change="onSortModeChange(($event.target as HTMLSelectElement).value as SortMode)"
      >
        <option value="manual">手动拖拽</option>
        <option value="priority">按优先级</option>
      </select>
    </div>

    <div class="filter-group">
      <label>视图：</label>
      <div class="view-toggle">
        <button
          class="btn-view"
          :class="{ active: viewMode === 'card' }"
          @click="onViewModeChange('card')"
          title="卡片视图"
        >
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
        </button>
        <button
          class="btn-view"
          :class="{ active: viewMode === 'list' }"
          @click="onViewModeChange('list')"
          title="列表视图"
        >
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useProjectsStore } from '../stores/projects'
import type { ViewMode, SortMode, ProjectFilters } from '../api/types'

const projectsStore = useProjectsStore()
const { filters, viewMode, sortMode } = storeToRefs(projectsStore)

function onFilterChange(key: keyof ProjectFilters, value: string) {
  projectsStore.setFilters({ [key]: value })
}

function onSortModeChange(mode: SortMode) {
  projectsStore.setSortMode(mode)
}

function onViewModeChange(mode: ViewMode) {
  projectsStore.setViewMode(mode)
}
</script>

<style scoped>
.filters {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
  padding: 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  margin-bottom: 24px;
  backdrop-filter: var(--backdrop-blur);
  box-shadow: var(--shadow-sm);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.filter-group select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-group select:hover {
  border-color: var(--primary-color);
}

.filter-group select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.view-toggle {
  display: flex;
  gap: 4px;
  background: var(--bg-color);
  padding: 4px;
  border-radius: 6px;
}

.btn-view {
  background: transparent;
  border: none;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.btn-view:hover {
  background: rgba(59, 130, 246, 0.1);
}

.btn-view.active {
  background: var(--primary-color);
  color: white;
}

.btn-view .icon {
  width: 18px;
  height: 18px;
  stroke: currentColor;
}

.btn-view.active .icon {
  stroke: white;
}
</style>
