# 接口契约（前端视角）

> 前端调用后端 API，详细格式见 specs/auth/03-api-contract.md 和 specs/research/03-api-contract.md。

---

## Auth API

### 注册
```
POST /api/v1/auth/register
Body: { username, password }
→ 201 | 400 | 409 | 429
```
`api/auth.ts` → `register(username, password)`

### 登录
```
POST /api/v1/auth/login
Body: { username, password, rememberMe? }
→ 200 (含 token + username) | 401 | 423 | 429
```
`api/auth.ts` → `login(username, password, rememberMe)` → 存储 token + username 到 localStorage

### 获取当前用户（Hydration）
```
GET /api/v1/auth/me
Auth: Bearer <token>
→ 200 (userId + username + status) | 401
```
`api/auth.ts` → `getMe()` → 前端首次加载时调用，校验 Token 有效性并恢复用户状态

### Token 刷新
```
POST /api/v1/auth/refresh
Auth: Bearer <token>
→ 200 (新 token) | 401 | 403
```
`api/auth.ts` → `refreshToken()` → Token 剩余 < 5 分钟时静默调用，更新 localStorage

### SSE Ticket 签发
```
POST /api/v1/auth/ticket
Auth: Bearer <token>
→ 200 (ticket + expiresIn)
```
`api/auth.ts` → `getTicket()` → 在连接 SSE 前调用，获取 30 秒短效 ticket

---

## Research API

### 发起新研究
```
POST /api/v1/research/new
Body: { topic, template }
→ 201 (researchId + plan) | 400 | 409 | 500
```

### 获取研究详情（任意阶段）
```
GET /api/v1/research/{id}
→ 200 (完整研究状态: topic/status/plan/subAgentResults/...) | 404
```
> 前端刷新页面时恢复当前研究状态；修改计划页按 F5 后重拉草稿

### 修改计划（同步，5-15 秒）
```
POST /api/v1/research/{id}/plan/revise
Body: { feedback }
→ 200 | 400 | 403 | 404 | 504
```
> **超时配置**: 30 秒；等待期间显示 Loading + 按钮禁用；超时后展示"计划生成超时，请重试"

### 确认计划
```
POST /api/v1/research/{id}/plan/confirm
→ 200 (含 streamUrl) | 400 | 404
```

### SSE 进度流
```
GET /api/v1/research/{id}/stream?ticket=<ticket>
→ text/event-stream
```
**连接流程**:
1. 确认计划后获得 `streamUrl`
2. 调用 `POST /api/v1/auth/ticket` 获取 30 秒短效 ticket
3. `new EventSource(\`${streamUrl}?ticket=${ticket}\`)`
4. 若连接中断需重连 → 重新获取 ticket 再重连

### 获取报告
```
GET /api/v1/research/{id}/report
→ 200 | 400 | 404
```

### 历史列表
```
GET /api/v1/research/history?page=1&pageSize=20
→ 200 (分页列表)
```

### 中断研究
```
POST /api/v1/research/{id}/cancel
→ 200
```

### 软删除
```
DELETE /api/v1/research/{id}
→ 200
```

### Token 统计
```
GET /api/v1/research/stats/tokens
→ 200
```

---

## 前端 API 层实现规范

### 文件结构
```
src/api/
├── client.ts       # Axios 实例 (baseURL, 拦截器, token 注入)
├── auth.ts          # Auth API (register/login/me/refresh/ticket)
└── research.ts      # Research API
```

### Token 管理
- 登录成功 → localStorage 存 token + username
- 请求拦截器 → 自动注入 `Authorization: Bearer <token>`
- 401 响应 → 尝试静默刷新（`/refresh`），刷新失败则清除 token 跳转 `/login`
  - **刷新竞态锁**: 多个并发请求同时收到 401 时，仅第一个触发刷新请求，其余请求等待刷新完成后统一重试，避免并发刷新导致多次无效 token 交换
- Token 剩余 < 5 分钟 → 自动调用 `/refresh` 刷新

### Hydration 流程
1. App 初始化 → `GET /api/v1/auth/me`
2. 若 401 → 跳转 `/login`
3. 若 200 → 恢复 `AuthState`，渲染受保护页面

### 错误处理
- 统一错误拦截器 → HTTP 错误码映射用户友好提示
- 429 Rate Limit → 提示并禁用按钮 60 秒
