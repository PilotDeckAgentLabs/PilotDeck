// Toast Notification Composable
import { ref } from 'vue'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface ToastState {
  show: boolean
  message: string
  type: ToastType
}

const toastState = ref<ToastState>({
  show: false,
  message: '',
  type: 'success',
})

let toastTimer: number | null = null

export function useToast() {
  function showToast(message: string, type: ToastType = 'success', duration = 2400) {
    toastState.value = {
      show: true,
      message,
      type,
    }

    if (toastTimer) {
      window.clearTimeout(toastTimer)
    }

    toastTimer = window.setTimeout(() => {
      toastState.value.show = false
    }, duration)
  }

  function hideToast() {
    toastState.value.show = false
    if (toastTimer) {
      window.clearTimeout(toastTimer)
      toastTimer = null
    }
  }

  return {
    toastState,
    showToast,
    hideToast,
  }
}
