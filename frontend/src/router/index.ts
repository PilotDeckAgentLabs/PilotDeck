// Vue Router Setup
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { checkAuth } from '../api/client'
import ProjectsPage from '../pages/ProjectsPage.vue'
import LoginPage from '../pages/LoginPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      name: 'projects',
      component: ProjectsPage,
      meta: { requiresAuth: true }
    },
    // Future routes can be added here:
    // { path: '/project/:id', name: 'project-detail', component: ProjectDetailPage }
  ],
})

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Check if route requires authentication
  const requiresAuth = to.meta.requiresAuth !== false
  
  // If already checking auth, wait
  if (authStore.isLoading) {
    next()
    return
  }
  
  // If not authenticated, check with server
  if (!authStore.isAuthenticated) {
    authStore.setLoading(true)
    try {
      const user = await checkAuth()
      if (user) {
        authStore.setUser(user)
      }
    } catch (error) {
      // Not authenticated
    } finally {
      authStore.setLoading(false)
    }
  }
  
  // Redirect logic
  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    // Redirect to home if already authenticated
    next('/')
  } else {
    next()
  }
})

export default router
