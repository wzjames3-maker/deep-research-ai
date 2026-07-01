# Task 08: Auth 工具函数

## 对应 Spec
- specs/auth/04-business-rules.md:
  - RULE-AUTH-001（bcrypt 加密策略）
  - RULE-AUTH-002（JWT 时效策略）
  - RULE-AUTH-004（登录成功重置计数）
  - RULE-AUTH-007（Token 刷新策略）
  - RULE-AUTH-008（SSE Ticket 策略）
- specs/auth/03-api-contract.md API-AUTH-006（Ticket 签发规则）

## 输入文件（Agent 需读取）
- specs/auth/04-business-rules.md
- specs/auth/03-api-contract.md（API-AUTH-006）
- src/config.py（JWT_SECRET, JWT_EXPIRES_IN, BCRYPT_ROUNDS）

## 输出文件
- `src/utils/bcrypt.py`（密码哈希工具）
- `src/utils/jwt.py`（JWT 创建/验证 + Ticket 生成/验证）
- `src/utils/ticket_store.py`（内存 Ticket 存储）

## 前置任务
- Task 01（config.py 中有 JWT_SECRET 等配置）

## 实现要求
1. **bcrypt 工具 (src/utils/bcrypt.py)**:
   - `hash_password(password: str) -> str`: bcrypt 哈希, cost=12
   - `verify_password(plain: str, hash: str) -> bool`: 验证
2. **JWT 工具 (src/utils/jwt.py)**:
   - `create_token(user_id: UUID, username: str, expires_delta: int = 86400) -> str`:
     - payload: `{ "sub": user_id, "username": username, "iat": now, "exp": now + expires_delta }`
     - 算法: HS256
     - `expires_delta` 默认 86400 (24h)，rememberMe=true 时传 604800 (7d)
   - `verify_token(token: str) -> dict`:
     - 解码 payload，检查 exp
     - 返回 payload dict 或抛出 `TokenInvalidError`
   - `decode_token(token: str) -> dict`:
     - 仅解码不验证 exp（供 auth middleware 内部使用）
3. **Ticket 工具 (src/utils/ticket_store.py)**:
   - 使用内存 `Dict[str, TicketEntry]` 存储
   - `create_ticket(user_id: UUID) -> str`: 生成 UUID ticket，30 秒过期，存储 `{ticket: {user_id, expires_at}}`
   - `verify_ticket(ticket: str) -> Optional[UUID]`: 验证 ticket 是否有效且未过期，返回 user_id 或 None
   - `cleanup_expired_tickets()`: 清理过期 ticket（定期调用或在每次 verify 时顺带清理）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] config.py 中 JWT_SECRET 已配置
- [ ] bcrypt 和 python-jose 已在 requirements.txt 中

### 功能验收
- [ ] `hash_password("MyPass123")` → 以 `$2b$12$` 开头
- [ ] `verify_password("MyPass123", hash)` → True
- [ ] `verify_password("wrong", hash)` → False
- [ ] `create_token(uuid, "test")` → 返回 3 段 JWT（header.payload.signature）
- [ ] `verify_token(token)` → 返回包含 sub, username, iat, exp 的 dict
- [ ] 过期 Token → `verify_token` 抛出 TokenInvalidError
- [ ] `create_ticket(uuid)` → 返回 UUID v4
- [ ] `verify_ticket(ticket)` 在 30 秒内 → 返回 user_id；30 秒后 → 返回 None

### AC 验收
- [ ] AC-AUTH-001: 注册后 JWT payload.sub = userId, payload.username = username（小写）
- [ ] AC-AUTH-004: 登录后 JWT exp - iat = 86400
- [ ] AC-AUTH-005: rememberMe=true → expiresIn = 604800
- [ ] AC-AUTH-015: Ticket expiresIn = 30，过期后验证失败

### 代码质量
- [ ] bcrypt rounds 从 config 读取（非硬编码）
- [ ] JWT key 从 config 读取（非硬编码）
- [ ] Ticket 存储有定期清理逻辑
- [ ] 无敏感信息打印

### 通过判定
全部 ✅ → 任务 Done，进入 Task 09
