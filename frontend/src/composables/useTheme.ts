// Theme Management Composable
import { ref, watch } from 'vue'

type Theme = 'light' | 'dark'

const currentTheme = ref<Theme>('light')

export function useTheme() {
  function initTheme() {
    const saved = localStorage.getItem('theme') as Theme | null
    currentTheme.value = saved || 'light'
    applyTheme(currentTheme.value)
  }

  function toggleTheme() {
    currentTheme.value = currentTheme.value === 'light' ? 'dark' : 'light'
    applyTheme(currentTheme.value)
    localStorage.setItem('theme', currentTheme.value)
  }

  function applyTheme(theme: Theme) {
    document.documentElement.setAttribute('data-theme', theme)
  }

  // Watch for external changes
  watch(currentTheme, (newTheme) => {
    applyTheme(newTheme)
  })

  return {
    currentTheme,
    initTheme,
    toggleTheme,
  }
}
