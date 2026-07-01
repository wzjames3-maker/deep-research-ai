# Task 23: 前端项目骨架

## 对应 Spec
- specs/frontend/00-overview.md（技术栈 + 路由表）
- specs/frontend/01-requirements.md REQ-FE-003（工作台状态驱动路由）
- specs/frontend/07-tech-constraints.md
- docs/tech-decision.md §决策3 ~ 决策5

## 输入文件（Agent 需读取）
- specs/frontend/00-overview.md（完整技术栈 + 路由定义）
- specs/frontend/07-tech-constraints.md

## 输出文件
- `frontend/` 目录下完整 Vite + React + TypeScript 项目
- `src/`
  - `main.tsx`（React 入口 + Router 挂载）
  - `App.tsx`（路由配置 + AuthProvider）
  - `api/client.ts`（axios instance + 拦截器）
  - `api/auth.ts`（Auth API 封装）
  - `api/research.ts`（Research API 封装）
  - `contexts/AuthContext.tsx`（认证状态管理）
  - `hooks/useAuth.ts`
  - `hooks/useSSE.ts`（SSE 连接 hook）
  - `pages/`（页面占位组件）
  - `components/`（通用组件目录）
  - `types/`（TypeScript 类型定义）

## 前置任务
- Task 01（FastAPI base URL 配置 → 前端 axios 对接）

## 实现要求

### 1. 初始化:
- `npm create vite@latest frontend -- --template react-ts`
- 安装依赖: `react-router-dom`, `axios`, `tailwindcss`, `shadcn/ui`, `react-markdown`, `remark-gfm`

### 2. 路由配置 (React Router v6):
```tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/register" element={<RegisterPage />} />
  <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
  <Route path="/research/new" element={<ProtectedRoute><NewResearchPage /></ProtectedRoute>} />
  <Route path="/research/:id" element={<ProtectedRoute><WorkbenchPage /></ProtectedRoute>} />
  <Route path="/research/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
</Routes>
```

### 3. Axios 拦截器 (`api/client.ts`):
```typescript
const client = axios.create({ baseURL: "/api/v1" });

// Request 拦截器: 注入 Authorization header
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response 拦截器: 处理 401 → 自动登出
client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
```

### 4. AuthContext (`contexts/AuthContext.tsx`):
- `token: string | null`
- `username: string | null`
- `isAuthenticated: boolean`
- `login(username, password, rememberMe)` → 调用 API, 存储 token
- `register(username, password)` → 调用 API, 自动登录
- `logout()` → 清除 localStorage, 跳转 /login
- `hydrate()` → App 启动时读取 localStorage 恢复登录态

### 5. API 封装:
- `api/auth.ts`: `login()`, `register()`, `me()`, `refresh()`, `ticket()`
- `api/research.ts`: `create()`, `get(id)`, `revise(id, feedback)`, `confirm(id)`, `cancel(id)`, `getReport(id)`, `listHistory(page, pageSize)`, `delete(id)`, `getTokenStats()`

### 6. SSE Hook (`hooks/useSSE.ts`):
```typescript
function useSSE(researchId: string) {
  // 1. 获取 ticket
  // 2. 建立 EventSource 连接: /research/{id}/stream?ticket={ticket}
  // 3. 事件回调: onSubAgentStart, onSubAgentComplete, onReportComplete, etc.
  // 4. 断线重连（重新获取 ticket）
  // 5. cleanup: close() on unmount
}
```

### 7. 类型定义 (`types/`):
- `Research`, `SubAgent`, `SubAgentResult`, `ResearchPlan`, `SSEEvent`, `TokenStats`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Node.js 18+ 可用
- [ ] FastAPI 后端已启动（可访问 `/api/v1/health`）

### 功能验收
- [ ] `npm run dev` → Vite 启动成功（localhost:5173）
- [ ] 访问 localhost:5173/login → 显示占位登录页（非 404）
- [ ] 访问 localhost:5173/dashboard → 自动重定向到 /login（未登录）
- [ ] localStorage 有 token → 访问 /dashboard → 不重定向
- [ ] API 调用 401 → 自动清除 token 并跳转 /login（AC-FE-015）

### AC 验收
- [ ] AC-FE-015: Token 过期 → API 401 → 自动跳转 /login, toast "登录已过期"

### 代码质量
- [ ] TypeScript 严格模式开启（`"strict": true`）
- [ ] Tailwind 配置正确（`tailwind.config.ts` 含 shadcn/ui 主题）
- [ ] shadcn/ui 组件库已初始化（`npx shadcn@latest init`）
- [ ] 路由使用 lazy loading（`React.lazy` + `Suspense`）优化首屏

### 通过判定
全部 ✅ → 任务 Done，进入 Task 24
