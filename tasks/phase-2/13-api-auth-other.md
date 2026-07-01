# Task 13: /me + /refresh + /ticket 接口

> **注**: 本任务为 3 个轻量端点合一，AC-AUTH-013~015 各自独立验收。如需严格 TDD，可分别拆为 test+impl 子任务。

## 对应 Spec
- specs/auth/03-api-contract.md:
  - API-AUTH-004: GET /auth/me
  - API-AUTH-005: POST /auth/refresh
  - API-AUTH-006: POST /auth/ticket
- specs/auth/06-acceptance.md AC-AUTH-013, 014, 015

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md（API-AUTH-004, 005, 006）
- specs/auth/06-acceptance.md（AC-AUTH-013, 014, 015）
- specs/auth/04-business-rules.md RULE-AUTH-002, 007, 008
- src/middleware/auth.py（get_current_user）
- src/utils/jwt.py（create_token, verify_token）
- src/utils/ticket_store.py（create_ticket, verify_ticket）
- src/api/auth/schemas.py（追加 MeResponse, RefreshResponse, TicketResponse）
- src/api/auth/service.py

## 输出文件
- `src/api/auth/schemas.py`（追加 3 个 Response Schema）
- `src/api/auth/router.py`（追加 3 个路由）
- `src/api/auth/service.py`（追加 3 个服务函数）
- `tests/auth/test_me_refresh_ticket.py`（集成测试）

## 前置任务
- Task 05（get_current_user 可用）
- Task 08（JWT + Ticket 工具可用）
- Task 10（fastapi auth router 已有 register）

## 实现要求

### 1. GET `/api/v1/auth/me` (API-AUTH-004)
- Auth: Bearer Token（get_current_user Depends）
- Response (200):
  ```json
  { "userId": "uuid", "username": "str", "status": "active" }
  ```
- 错误: 401 TOKEN_INVALID
- **用途**: 前端页面刷新时 Hydration（恢复登录态）
- 无需 rate limit（高性能查询）

### 2. POST `/api/v1/auth/refresh` (API-AUTH-005)
- Auth: Bearer Token
- Body: 无
- Response (200):
  ```json
  { "token": "str (新 JWT)", "expiresIn": 86400 }
  ```
- 错误: 401 TOKEN_INVALID, 403 ACCOUNT_LOCKED
- 规则:
  - 用任意有效 Token（含即将过期的）换取新 Token
  - 新 Token 固定 24 小时（不继承 rememberMe 的 7 天）
  - 检查用户 status=active（locked 用户拒绝刷新）
- Rate limit: 30 次/分钟/用户（通过 get_current_user 的 user_id 限流）

### 3. POST `/api/v1/auth/ticket` (API-AUTH-006)
- Auth: Bearer Token
- Body: 无
- Response (200):
  ```json
  { "ticket": "str (UUID v4)", "expiresIn": 30 }
  ```
- 规则:
  - 调用 Task 08 的 `create_ticket(current_user.id)`
  - Ticket 30 秒有效，仅用于 SSE 认证
- 无需额外 rate limit（调用频率由 SSE 重连策略自然控制）

### 4. 测试
- `tests/auth/test_me_refresh_ticket.py`:
  - test_me_success: 有效 Token → 200 + 用户信息
  - test_me_token_invalid: 非法 Token → 401
  - test_refresh_success: 有效 Token → 新 JWT
  - test_refresh_when_locked: locked 用户 → 403 ACCOUNT_LOCKED
  - test_ticket_success: 有效 Token → UUID ticket + expiresIn=30
  - test_ticket_expired: 30 秒后验证 ticket → 失败

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 05 get_current_user 可正确解析 Token 并返回 User
- [ ] Task 08 create_token / create_ticket 可用
- [ ] Task 10 router 已注册

### AC 验收
- [ ] AC-AUTH-013: GET /auth/me → 200, userId/username/status 正确；无效 Token → 401
- [ ] AC-AUTH-014: POST /auth/refresh → 200, 新 JWT ≠ 旧 JWT, expiresIn=86400；locked 用户 → 403
- [ ] AC-AUTH-015: POST /auth/ticket → 200, UUID v4, expiresIn=30；过期 → 401

### 代码质量
- [ ] /me 无 Rate limit 依赖（高性能）
- [ ] /refresh 使用 get_current_user 的 user_id 做限流 key（30/min/user）
- [ ] /ticket 生成 UUID v4 格式的 ticket
- [ ] 所有 3 个接口的测试通过

### 通过判定
全部 ✅ → 任务 Done。Auth 模块完成，进入 Phase 3 (Research 基础设施)
