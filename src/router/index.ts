import { createRouter, createWebHistory } from 'vue-router'
import BrainDashboardView from '@/views/BrainDashboardView.vue'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'brain-dashboard',
      component: BrainDashboardView,
    },
  ],
})
