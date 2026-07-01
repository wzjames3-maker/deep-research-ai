# 业务规则

## 来源
PRD.md §3 UC-001/UC-002 主流程/替代流程/异常流程

---

## RULE-AUTH-001: 密码加密

- **触发**: 注册（API-AUTH-001）
- **规则**:
  - 使用 bcrypt 哈希，cost factor = 12
  - 通过 `passlib.context.CryptContext` 统一管理
  - 存储字段为 `password_hash`，永远不存明文
- **禁止**: 明文存储、MD5、SHA1、SHA256 等快速哈希

---

## RULE-AUTH-002: JWT 签发

- **触发**: 注册成功、登录成功
- **规则**:
  - Payload: `{ sub: userId, username, iat, exp }`
  - `exp = iat + expiresIn`（24h 或 7d）
  - 签名算法: HS256
  - Secret: 从环境变量 `JWT_SECRET` 读取（≥ 32 字符），不存在则启动失败
- **禁止**: Payload 中包含 password_hash 等敏感信息
- **默认有效期**:
  - `rememberMe=false` → 24 小时 (86400s)
  - `rememberMe=true` → 7 天 (604800s)

---

## RULE-AUTH-003: 登录失败锁定

- **触发**: 密码验证失败
- **规则**:
  1. `failed_login_count += 1`
  2. 当 `failed_login_count ≥ 5`:
     - `status = 'locked'`
     - `locked_until = NOW() + 15 分钟`
  3. 锁定期间所有登录尝试返回 423（不更新计数器）
  4. 锁定过期后自动恢复

---

## RULE-AUTH-004: 登录成功重置

- **触发**: 密码验证成功
- **规则**:
  1. `failed_login_count = 0`
  2. `locked_until = NULL`
  3. `status` 若为 `locked` → 改为 `active`
  4. 更新 `remember_me` 字段

---

## RULE-AUTH-005: 账号规范化

- **触发**: 注册、登录
- **规则**:
  1. 去除首尾空白符（`.strip()`）
  2. 统一转换为小写（`.lower()`）
  3. 校验格式：3-50 字符，仅允许 `[a-z0-9_]`
  4. 规范化后的值用于存储和查询
- **禁止**: 大小写敏感匹配、含特殊字符的账号名

---

## RULE-AUTH-006: 密码强度校验

- **触发**: 注册
- **规则**:
  1. 长度: 8-64 字符
  2. 至少包含 1 个字母 (A-Za-z)
  3. 至少包含 1 个数字 (0-9)
- **校验正则**:
  - 包含字母: `/[A-Za-z]/`
  - 包含数字: `/[0-9]/`
  - Python 等效: `re.search(r'[A-Za-z]', password)` 且 `re.search(r'[0-9]', password)`
- **禁止**: 仅数字、仅字母

---

## RULE-AUTH-007: Token 刷新

- **触发**: `POST /api/v1/auth/refresh`（有有效 Token 时）
- **规则**:
  1. 用当前有效 Token 换发新 Token
  2. 新旧 Token 短期内均可使用（不立即吊销旧 Token）
  3. 新 Token 有效期固定 24 小时
  4. 若账号已锁定 → 拒绝刷新，返回 403
- **向前端建议**: Token 剩余有效期 < 5 分钟时静默调用刷新

---

## RULE-AUTH-008: SSE Ticket 签发

- **触发**: `POST /api/v1/auth/ticket`
- **规则**:
  1. 生成随机 UUID v4 作为 ticket
  2. 服务端内存存储 `{ ticket: { userId, expiresAt: now+30s } }`
  3. 不持久化，服务重启后 ticket 全部失效
  4. Ticket 仅用于 SSE 端点认证，不可用于其他 API
- **过期清理策略**:
  1. 惰性清理: 每次 ticket 验证时顺便清除已过期条目
  2. 单用户限制: 同一用户最多同时持有 3 个有效 ticket，超出则清除最早的 ticket
  3. 无需后台定时任务（避免引入额外复杂度）
- **用途**: 避免将长期 JWT 暴露在 Nginx Access Log 的 URL query string 中
