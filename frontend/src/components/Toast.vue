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
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  background: var(--card-bg);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
  z-index: 9999;
}

.toast.show {
  opacity: 1;
  pointer-events: auto;
}

.toast.success {
  background: var(--success-color);
  color: white;
}

.toast.error {
  background: var(--danger-color);
  color: white;
}

.toast.info {
  background: var(--info-color);
  color: white;
}

.toast.warning {
  background: var(--warning-color);
  color: white;
}
</style>
