<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <strong>MyProjectManager</strong>
        <span class="muted">Vue 3 + Vite + TS (WIP)</span>
      </div>
      <nav class="nav">
        <a class="nav-link" href="/">旧版</a>
        <a class="nav-link" href="/api/meta" target="_blank" rel="noreferrer">API</a>
      </nav>
    </header>

    <main class="app-main">
      <section class="card">
        <h1>新前端正在重构中</h1>
        <p class="muted">
          目标：更好的可维护性/可扩展性（Projects、Agent Timeline、Runs、Actions）。
        </p>
        <p>
          当前旧版 UI 仍在 <a href="/">/</a>；新 UI build 后可通过 <a href="/app">/app</a> 访问。
        </p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--bg-gradient);
  color: var(--text-primary);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(37, 99, 235, 0.85));
  color: #fff;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav {
  display: flex;
  gap: 10px;
}

.nav-link {
  color: #fff;
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.12);
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.18);
}

.app-main {
  max-width: 980px;
  margin: 0 auto;
  padding: 24px 16px;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  box-shadow: var(--shadow);
  padding: 22px;
}

.muted {
  color: rgba(255, 255, 255, 0.85);
}

.card .muted {
  color: var(--text-secondary);
}
</style>
