<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1 class="login-title">PilotDeck</h1>
        <p class="login-subtitle">ProjectOps × AgentOps 控制台</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username" class="form-label">用户名</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="form-input"
            placeholder="admin"
            required
            autocomplete="username"
            :disabled="isLoading"
          />
        </div>

        <div class="form-group">
          <label for="password" class="form-label">密码</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="请输入密码"
            required
            autocomplete="current-password"
            :disabled="isLoading"
          />
        </div>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          class="login-button"
          :disabled="isLoading"
        >
          <span v-if="!isLoading">登录</span>
          <span v-else>登录中...</span>
        </button>
      </form>

      <div class="login-footer">
        <p class="hint">默认账号: admin / admin</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { login } from '../api/client'
import { useToast } from '../composables/useToast'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    errorMessage.value = '请输入用户名和密码'
    return
  }

  errorMessage.value = ''
  isLoading.value = true

  try {
    const user = await login({
      username: username.value,
      password: password.value,
    })

    authStore.setUser(user)
    toast.success('登录成功')
    router.push('/')
  } catch (error: any) {
    errorMessage.value = error.message || '登录失败，请检查用户名和密码'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: var(--bg-gradient);
}

.login-container {
  width: 100%;
  max-width: 420px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--border-radius);
  padding: 3rem 2.5rem;
  box-shadow: var(--shadow-lg);
}

.login-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.login-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.login-subtitle {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  color: var(--text-primary);
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  transition: all 0.2s;
  font-family: inherit;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-input::placeholder {
  color: var(--text-muted);
}

.error-message {
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: var(--danger-color);
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--border-radius-sm);
}

.login-button {
  width: 100%;
  padding: 0.875rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: #ffffff;
  background: var(--primary-color);
  border: none;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.login-button:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.login-button:active:not(:disabled) {
  transform: translateY(0);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.login-footer {
  margin-top: 2rem;
  text-align: center;
}

.hint {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
</style>
