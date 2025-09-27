import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { useConnectionStore } from '@/stores/connection'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'connection',
      component: HomeView
    },
    {
      path: '/control',
      name: 'control',
      component: () => import('../views/ControlView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../views/ConfigView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('../views/LogsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/agent',
      name: 'agent',
      component: () => import('../views/AgentView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/chatbot',
      name: 'chatbot',
      component: () => import('../views/ChatBotView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, from, next) => {
  // Pinia store must be instantiated within the guard
  const connectionStore = useConnectionStore();
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);

  if (requiresAuth && !connectionStore.isConnected) {
    next({ name: 'connection' });
  } else {
    next();
  }
});

export default router
