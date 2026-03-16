import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Mock components to avoid import issues
const mockComponent = { template: '<div>Mock</div>' }

// Define routes like in the actual router
const routes = [
  {
    path: '/login',
    name: 'login',
    component: mockComponent,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'home',
    component: mockComponent,
    meta: { requiresAuth: true }
  },
  {
    path: '/simulator/:id',
    name: 'simulator',
    component: mockComponent,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: mockComponent,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: mockComponent,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

describe('Router Navigation Guards', () => {
  let router
  let pinia

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)

    router = createRouter({
      history: createWebHistory(),
      routes
    })

    // Add the navigation guard
    router.beforeEach((to, from, next) => {
      const authStore = useAuthStore()

      if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next({ name: 'login', query: { redirect: to.fullPath } })
      } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
        next({ name: 'home' })
      } else if (to.name === 'login' && authStore.isAuthenticated) {
        next({ name: 'home' })
      } else {
        next()
      }
    })
  })

  describe('unauthenticated user', () => {
    it('should redirect to login when accessing protected route', async () => {
      const authStore = useAuthStore()
      authStore.user = null
      authStore.token = null

      await router.push('/')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('login')
    })

    it('should allow access to login page', async () => {
      const authStore = useAuthStore()
      authStore.user = null
      authStore.token = null

      await router.push('/login')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('login')
    })

    it('should include redirect query when redirecting to login', async () => {
      const authStore = useAuthStore()
      authStore.user = null
      authStore.token = null

      await router.push('/simulator/123')
      await router.isReady()

      expect(router.currentRoute.value.query.redirect).toBe('/simulator/123')
    })
  })

  describe('authenticated non-admin user', () => {
    beforeEach(() => {
      const authStore = useAuthStore()
      authStore.user = { username: 'testuser', role: 'user' }
      authStore.token = 'valid-token'
    })

    it('should allow access to home', async () => {
      await router.push('/')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })

    it('should allow access to simulator detail', async () => {
      await router.push('/simulator/1')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('simulator')
    })

    it('should redirect away from login page', async () => {
      await router.push('/login')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })

    it('should redirect from admin to home', async () => {
      await router.push('/admin')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })

    it('should redirect from admin sub-routes to home', async () => {
      await router.push('/admin/users')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })
  })

  describe('authenticated admin user', () => {
    beforeEach(() => {
      const authStore = useAuthStore()
      authStore.user = { username: 'admin', role: 'admin' }
      authStore.token = 'valid-token'
    })

    it('should allow access to admin routes', async () => {
      await router.push('/admin')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('admin')
    })

    it('should allow access to admin sub-routes', async () => {
      await router.push('/admin/users')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('admin-users')
    })

    it('should allow access to regular routes', async () => {
      await router.push('/')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })

    it('should redirect away from login page', async () => {
      await router.push('/login')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })
  })
})
