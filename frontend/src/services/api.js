/**
 * API Service
 * Axios instance configured for the SimPortControl API
 */
import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push({ name: 'login' })
    }
    return Promise.reject(error)
  }
)

export default api

// Convenience methods for specific endpoints
export const authApi = {
  login: (username, password) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) => api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  })
}

export const simulatorsApi = {
  list: () => api.get('/simulators'),
  get: (id) => api.get(`/simulators/${id}`),
  create: (data) => api.post('/simulators', data),
  update: (id, data) => api.put(`/simulators/${id}`, data),
  delete: (id) => api.delete(`/simulators/${id}`)
}

export const portsApi = {
  getStatus: (id) => api.get(`/ports/${id}`),
  enable: (id, options = {}) => api.post(`/ports/${id}/enable`, options),
  disable: (id) => api.post(`/ports/${id}/disable`),
  forceEnable: (id, reason) => api.post(`/ports/${id}/force-enable`, { reason }),
  forceDisable: (id) => api.post(`/ports/${id}/force-disable`),
  listAssignments: () => api.get('/ports/assignments'),
  createAssignment: (data) => api.post('/ports/assignments', data),
  updateAssignment: (id, data) => api.put(`/ports/assignments/${id}`, data),
  deleteAssignment: (id) => api.delete(`/ports/assignments/${id}`)
}

export const switchesApi = {
  list: () => api.get('/switches'),
  get: (id) => api.get(`/switches/${id}`),
  create: (data) => api.post('/switches', data),
  update: (id, data) => api.put(`/switches/${id}`, data),
  delete: (id) => api.delete(`/switches/${id}`),
  test: (id) => api.post(`/switches/${id}/test`)
}

export const usersApi = {
  list: () => api.get('/users'),
  get: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`)
}

export const logsApi = {
  list: (params = {}) => api.get('/logs', { params }),
  clear: () => api.delete('/logs')
}

export const systemApi = {
  health: () => api.get('/system/health'),
  info: () => api.get('/system/info'),
  ssl: () => api.get('/system/ssl'),
  renewSsl: (dryRun = false) => api.post('/system/ssl/renew', null, { params: { dry_run: dryRun }, timeout: 120000 })
}

export const discoveryApi = {
  scanSwitch: (switchId) => api.post(`/discovery/switches/${switchId}/scan`),
  getSwitchPorts: (switchId) => api.get(`/discovery/switches/${switchId}/ports`),
  getAllPorts: (status = null) => api.get('/discovery/ports', { params: { status } }),
  assignPort: (data) => api.post('/discovery/ports/assign', data),
  releasePort: (assignmentId) => api.delete(`/discovery/ports/assignments/${assignmentId}`),
  refreshPort: (portId) => api.post(`/discovery/ports/${portId}/refresh`),
}
