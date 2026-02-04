<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ isEditMode ? '编辑项目' : '添加项目' }}</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="name">项目名称 <span class="required">*</span></label>
          <input 
            v-model="formData.name" 
            type="text" 
            id="name" 
            required 
            placeholder="请输入项目名称"
          />
        </div>

        <div class="form-group">
          <label for="description">项目描述</label>
          <textarea 
            v-model="formData.description" 
            id="description" 
            rows="3"
            placeholder="请输入项目描述"
          ></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="status">状态</label>
            <select v-model="formData.status" id="status">
              <option value="planning">计划中</option>
              <option value="in-progress">进行中</option>
              <option value="paused">暂停</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>

          <div class="form-group">
            <label for="priority">优先级</label>
            <select v-model="formData.priority" id="priority">
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
              <option value="urgent">紧急</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="progress">进度 (%)</label>
            <input 
              v-model.number="formData.progress" 
              type="number" 
              id="progress" 
              min="0" 
              max="100"
            />
          </div>

          <div class="form-group">
            <label for="costTotal">成本（已花费，元）</label>
            <input 
              v-model.number="formData.costTotal" 
              type="number" 
              id="costTotal" 
              min="0" 
              step="0.01"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="revenueTotal">收入（目前收入，元）</label>
          <input 
            v-model.number="formData.revenueTotal" 
            type="number" 
            id="revenueTotal" 
            min="0" 
            step="0.01"
          />
        </div>

        <div class="form-group">
          <label for="github">Github 仓库</label>
          <input 
            v-model="formData.github" 
            type="text" 
            id="github"
            placeholder="如: https://github.com/user/repo"
          />
        </div>

        <div class="form-group">
          <label for="workspace">工作目录</label>
          <input 
            v-model="formData.workspace" 
            type="text" 
            id="workspace"
            placeholder="如: E:/Projects/MyProject"
          />
        </div>

        <div class="form-group">
          <label for="notes">备注</label>
          <textarea 
            v-model="formData.notes" 
            id="notes" 
            rows="2"
            placeholder="请输入备注"
          ></textarea>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">
            取消
          </button>
          <button type="submit" class="btn btn-primary">
            保存
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { Project, ProjectFormData, ProjectStatus, ProjectPriority } from '../api/types'

const props = defineProps<{
  show: boolean
  project: Project | null
}>()

const emit = defineEmits<{
  close: []
  save: [data: ProjectFormData]
}>()

const isEditMode = computed(() => props.project !== null)

const formData = ref<ProjectFormData>({
  name: '',
  description: '',
  notes: '',
  status: 'planning' as ProjectStatus,
  priority: 'medium' as ProjectPriority,
  progress: 0,
  costTotal: 0,
  revenueTotal: 0,
  github: '',
  workspace: '',
})

// Reset form when project changes
watch(() => props.project, (project) => {
  if (project) {
    formData.value = {
      name: project.name,
      description: project.description || '',
      notes: project.notes || '',
      status: project.status,
      priority: project.priority,
      progress: project.progress,
      costTotal: project.cost.total,
      revenueTotal: project.revenue.total,
      github: project.github || '',
      workspace: project.workspace || '',
    }
  } else {
    // Reset to defaults for add mode
    formData.value = {
      name: '',
      description: '',
      notes: '',
      status: 'planning',
      priority: 'medium',
      progress: 0,
      costTotal: 0,
      revenueTotal: 0,
      github: '',
      workspace: '',
    }
  }
}, { immediate: true })

function handleSubmit() {
  emit('save', formData.value)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  backdrop-filter: var(--backdrop-blur);
  border-radius: 12px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

form {
  padding: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.required {
  color: var(--danger-color);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-group textarea {
  resize: vertical;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: var(--bg-color);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--border-color);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}
</style>
