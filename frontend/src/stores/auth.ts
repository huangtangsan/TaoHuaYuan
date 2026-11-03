import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchInfo, login as loginApi, logout as logoutApi, type MenuItem } from '@/api/user'

export const useAuthStore = defineStore('auth', () => {
  const username = ref('')
  const menu = ref<MenuItem[]>([])
  const loaded = ref(false)

  async function ensureUser(): Promise<void> {
    if (loaded.value) return
    const info = await fetchInfo()
    username.value = info.username
    menu.value = info.menu ?? []
    loaded.value = true
  }

  async function login(name: string, password: string): Promise<void> {
    // The backend sets an HttpOnly cookie on login, so the token never has to be
    // written (and exposed) through document.cookie.
    await loginApi(name, password)
    loaded.value = false
    await ensureUser()
  }

  async function logout(): Promise<void> {
    try {
      await logoutApi()
    } finally {
      username.value = ''
      menu.value = []
      loaded.value = false
    }
  }

  return { username, menu, loaded, ensureUser, login, logout }
})
