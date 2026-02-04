// Vue Router Setup
import { createRouter, createWebHistory } from 'vue-router'
import ProjectsPage from '../pages/ProjectsPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'projects',
      component: ProjectsPage,
    },
    // Future routes can be added here:
    // { path: '/project/:id', name: 'project-detail', component: ProjectDetailPage }
  ],
})

export default router
