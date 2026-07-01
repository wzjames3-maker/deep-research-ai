# 验收标准

## 来源
REQ-AUTH-001/002/003 + RULE-AUTH-001 ~ 008 + EC-AUTH-001 ~ 009

---

## AC-AUTH-001: 正常注册 (REQ-AUTH-001 + RULE-AUTH-001 + RULE-AUTH-005)

- **Given**: 数据库无该用户
- **When**: POST `/api/v1/auth/register` `{ "username": " ZhangSan ", "password": "MyPass123" }`
- **Then**:
  - [ ] HTTP 201
  - [ ] response.userId 是合法 UUID
  - [ ] response.username = "zhangsan"（已 lowercase + trim）
  - [ ] response.token 是合法 JWT（3 段）
  - [ ] JWT payload.sub = userId, payload.username = "zhangsan"
  - [ ] response.expiresIn = 86400
  - [ ] 数据库 password_hash 以 $2b$ 开头（bcrypt）

---

## AC-AUTH-002: 弱密码注册被拒绝 (RULE-AUTH-006)

- **Given**: 无
- **When**: POST `/api/v1/auth/register` `{ "username": "test", "password": "1234" }`
- **Then**:
  - [ ] HTTP 400 INVALID_PASSWORD

---

## AC-AUTH-003: 重复注册 (EC-AUTH-001)

- **Given**: 已存在用户 username="dupe"
- **When**: 用 username="Dupe" 再次注册
- **Then**:
  - [ ] HTTP 409 USERNAME_EXISTS

---

## AC-AUTH-004: 正常登录 (REQ-AUTH-002 + RULE-AUTH-002 + RULE-AUTH-004)

- **Given**: 已注册用户 { username: "user1", password: "Pass1234" }
- **When**: POST `/api/v1/auth/login` `{ "username": "user1", "password": "Pass1234" }`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.username = "user1"
  - [ ] response.token 可用 JWT_SECRET 验证
  - [ ] JWT exp - iat = 86400
  - [ ] response.expiresIn = 86400
  - [ ] 数据库 failed_login_count = 0

---

## AC-AUTH-005: 记住我 (RULE-AUTH-002)

- **Given**: AC-AUTH-004 的用户
- **When**: POST `/api/v1/auth/login` `{ "username": "user1", "password": "Pass1234", "rememberMe": true }`
- **Then**:
  - [ ] response.expiresIn = 604800 (7天)
  - [ ] JWT exp - iat = 604800

---

## AC-AUTH-006: 密码错误 (RULE-AUTH-003)

- **Given**: AC-AUTH-004 的用户，failed_login_count = 0
- **When**: POST `/api/v1/auth/login` `{ "username": "user1", "password": "wrong" }`
- **Then**:
  - [ ] HTTP 401 INVALID_CREDENTIALS
  - [ ] 数据库 failed_login_count = 1

---

## AC-AUTH-007: 账户锁定 (RULE-AUTH-003 + EC-AUTH-003)

- **Given**: 用户 failed_login_count = 4
- **When**: 第 5 次用错误密码登录
- **Then**:
  - [ ] HTTP 401
  - [ ] 数据库 status = 'locked', locked_until ≈ NOW() + 15min
  - [ ] 第 6 次用正确密码 → HTTP 423 ACCOUNT_LOCKED

---

## AC-AUTH-008: 锁定期间用正确密码 (EC-AUTH-004)

- **Given**: 用户 status='locked', locked_until 未过期
- **When**: 用正确密码登录
- **Then**:
  - [ ] HTTP 423 ACCOUNT_LOCKED
  - [ ] failed_login_count 不变

---

## AC-AUTH-009: 锁定期满自动恢复

- **Given**: 用户 status='locked', locked_until 已过期
- **When**: 用正确密码登录
- **Then**:
  - [ ] HTTP 200（自动解锁并登录成功）
  - [ ] status = 'active', failed_login_count = 0

---

## AC-AUTH-010: Token 无效 (EC-AUTH-005)

- **When**: 用篡改/已过期的 Token 访问认证端点
- **Then**: HTTP 401 TOKEN_INVALID

---

## AC-AUTH-011: 账号大小写不敏感 (RULE-AUTH-005)

- **Given**: 已注册 "ZHANGSAN"
- **When**: 登录 username="zhangsan"
- **Then**: HTTP 200（登录成功）

---

## AC-AUTH-012: 速率限制 (EC-AUTH-008)

- **Given**: 同一 IP
- **When**: 连续 POST `/api/v1/auth/login` > 10 次/分钟
- **Then**: 第 11 次返回 HTTP 429 RATE_LIMITED

---

## AC-AUTH-013: 获取当前用户 (API-AUTH-004)

- **Given**: 已登录，持有有效 Token
- **When**: GET `/api/v1/auth/me`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.userId 正确
  - [ ] response.username 正确
  - [ ] response.status = "active"
- **Given**: Token 无效
- **When**: GET `/api/v1/auth/me`
- **Then**: HTTP 401 TOKEN_INVALID

---

## AC-AUTH-014: Token 刷新 (API-AUTH-005 + RULE-AUTH-007)

- **Given**: 持有有效 Token
- **When**: POST `/api/v1/auth/refresh`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.token 是新 JWT（与旧 Token 不同）
  - [ ] expiresIn = 86400
  - [ ] 旧 Token 在刷新后 5 秒内仍可用
- **Given**: 账号已锁定
- **When**: POST `/api/v1/auth/refresh`
- **Then**: HTTP 403 ACCOUNT_LOCKED

---

## AC-AUTH-015: SSE Ticket 签发 (API-AUTH-006 + RULE-AUTH-008)

- **Given**: 持有有效 Token
- **When**: POST `/api/v1/auth/ticket`
- **Then**:
  - [ ] HTTP 200
  - [ ] response.ticket 是 UUID v4 格式
  - [ ] expiresIn = 30
  - [ ] 30 秒后用此 ticket 访问 SSE → 401

---

## AC-AUTH-016: 注册接口速率限制 (API-AUTH-001 Rate Limit)

- **Given**: 同一 IP
- **When**: 连续 POST `/api/v1/auth/register` > 5 次/分钟
- **Then**: 第 6 次返回 HTTP 429 RATE_LIMITED

---

## 未覆盖场景（V1 已知缺口）
- EC-AUTH-009 (数据库连接失败 → 503): 需要集成测试环境模拟 DB 断开，V1 暂不覆盖
- EC-AUTH-006 (JWT_SECRET 未配置): 启动配置级检查，非 API 测试范畴

