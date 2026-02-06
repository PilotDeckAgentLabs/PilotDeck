// Auth Store - Manages user authentication state
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface User {
  id: string
  username: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const isLoading = ref(false)

  // Getters
  const isAuthenticated = computed(() => user.value !== null)

  // Actions
  function setUser(newUser: User | null) {
    user.value = newUser
  }

  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  function clearUser() {
    user.value = null
  }

  return {
    // State
    user,
    isLoading,
    // Getters
    isAuthenticated,
    // Actions
    setUser,
    setLoading,
    clearUser,
  }
})
