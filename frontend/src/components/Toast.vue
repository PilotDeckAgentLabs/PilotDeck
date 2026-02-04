<template>
  <div class="toast" :class="{ show: toastState.show, [toastState.type]: true }">
    {{ toastState.message }}
  </div>
</template>

<script setup lang="ts">
import { useToast } from '../composables/useToast'

const { toastState } = useToast()
</script>

<style scoped>
.toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  padding: 10px 24px;
  border-radius: 9999px; /* Pill shape */
  background: var(--card-bg);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  opacity: 0;
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 9999;
  font-weight: 500;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
  pointer-events: auto;
}

.toast.success {
  background: var(--success-color);
  color: white;
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3);
}

.toast.error {
  background: var(--danger-color);
  color: white;
  box-shadow: 0 8px 20px rgba(239, 68, 68, 0.3);
}

.toast.info {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3);
}

.toast.warning {
  background: var(--warning-color);
  color: white;
}
</style>
