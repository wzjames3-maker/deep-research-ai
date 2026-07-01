# 接口契约

## 来源
PRD.md §3 UC-001/UC-002 + REQ-AUTH-001/002/003

## 公共前缀
`/api/v1/auth`

---

## API-AUTH-001: 用户注册

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/auth/register` |
| **Auth** | 不需要 |

### Request Body
```json
{
  "username": "string (required, 3-50 chars, 仅允许字母、数字、下划线)",
  "password": "string (required, 8-64 chars, 至少包含 1 个字母和 1 个数字)"
}
```

### Success Response (201)
```json
{
  "userId": "uuid",
  "username": "string",
  "token": "string (JWT)",
  "expiresIn": 86400
}
```

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 400 | INVALID_USERNAME | 账号格式无效（3-50字符，仅字母数字下划线） | username 不符合规则 |
| 400 | INVALID_PASSWORD | 密码长度应为 8-64 字符，且至少包含 1 个字母和 1 个数字 | 密码不符合规则 |
| 409 | USERNAME_EXISTS | 该账号已被注册 | username 已存在 |
| 429 | RATE_LIMITED | 请求过于频繁，请稍后重试 | 超过频率限制 |

### Rate Limit: 5 次/分钟/IP

---

## API-AUTH-002: 用户登录

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/auth/login` |
| **Auth** | 不需要 |

### Request Body
```json
{
  "username": "string (required)",
  "password": "string (required)",
  "rememberMe": "boolean (optional, default: false)"
}
```

### Success Response (200)
```json
{
  "userId": "uuid",
  "username": "string",
  "token": "string (JWT)",
  "expiresIn": 86400
}
```
> `expiresIn`: 86400 (24h) for 常规登录, 604800 (7d) for rememberMe=true

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 401 | INVALID_CREDENTIALS | 账号或密码错误 | 账号不存在或密码错误 |
| 423 | ACCOUNT_LOCKED | 账户已锁定，请 {minutes} 分钟后重试 | status='locked' AND locked_until > NOW() |
| 429 | RATE_LIMITED | 请求过于频繁，请稍后重试 | 超过频率限制 |

### Rate Limit: 10 次/分钟/IP

---

## API-AUTH-003: 验证 Token (内部中间件)

| 属性 | 值 |
|---|---|
| **用途** | FastAPI Dependency，注入到所有需要认证的路由 |
| **Header** | `Authorization: Bearer <token>` |
| **成功** | 注入 `current_user` 到路由参数 |
| **失败** | 返回 401 `{ "code": "TOKEN_INVALID" }` |

### 验证逻辑
1. 提取 Bearer token
2. 用 `JWT_SECRET` 验证签名 (HS256)
3. 检查 `exp` 是否过期
4. 解析 payload 中的 userId，查询数据库确认用户存在
5. 将 User 对象注入到 FastAPI 路由的 `current_user` 参数
   - **注意**: 不在此层检查 locked 状态。各端点自行决定是否允许 locked 用户访问：
     - POST /login → locked 用户返回 423（RULE-AUTH-003）
     - POST /refresh → locked 用户返回 403（RULE-AUTH-007）
     - GET /me → 允许 locked 用户查看自身信息

---

## API-AUTH-004: 获取当前用户信息

| 属性 | 值 |
|---|---|
| **Method** | GET |
| **Path** | `/api/v1/auth/me` |
| **Auth** | Bearer Token |

### Success Response (200)
```json
{
  "userId": "uuid",
  "username": "string",
  "status": "active"
}
```

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 401 | TOKEN_INVALID | Token 无效或已过期 | — |

### 用途: 前端刷新页面时校验 Token 是否有效，获取当前用户信息（Hydration）

---

## API-AUTH-005: Token 刷新

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/auth/refresh` |
| **Auth** | Bearer Token |

### Request Body: 无

### Success Response (200)
```json
{
  "token": "string (新 JWT)",
  "expiresIn": 86400
}
```

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 401 | TOKEN_INVALID | Token 无效或已过期 | — |
| 403 | ACCOUNT_LOCKED | 账户已锁定 | 账号 status='locked' |

### 规则
- 用有效 Token 换取新 Token（新旧均可短暂共存，不支持旧 Token 吊销）
- 新 Token 有效期 = 24 小时（不继承 rememberMe 的 7 天）
- 前端在 Token 剩余 < 5 分钟时静默调用此接口刷新

### Rate Limit: 30 次/分钟/用户

---

## API-AUTH-006: 签发 SSE Ticket

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/auth/ticket` |
| **Auth** | Bearer Token |

### Request Body: 无

### Success Response (200)
```json
{
  "ticket": "string (UUID v4)",
  "expiresIn": 30
}
```

### 规则
- 签发一个短效 Ticket（30 秒过期），用于 SSE 连接认证
- Ticket 服务端内存存储（`{ ticket → { userId, expiresAt } }` 字典），不持久化
- 目的是避免将长期 JWT 暴露在 Nginx Access Log 的 URL 参数中
- Ticket 仅可用于建立 SSE 连接，不可用于其他 API 调用
