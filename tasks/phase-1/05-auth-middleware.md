# Task 05: 认证中间件 (JWT Depends)

## 对应 Spec
- specs/auth/03-api-contract.md API-AUTH-003（验证 Token）

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md API-AUTH-003（验证逻辑 5 步）
- specs/auth/04-business-rules.md RULE-AUTH-002（JWT 签发规则）
- src/config.py（JWT_SECRET 等配置）
- src/models/base.py（get_db）
- src/errors.py（TokenInvalidError, AccountLockedError）

## 输出文件
- `src/middleware/auth.py`（`get_current_user` Depends 函数）

## 前置任务
- Task 01（项目骨架）
- Task 02（User 模型已存在）
- Task 03（TokenInvalidError 已定义）

## 实现要求
1. **`get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db))`**:
   - 使用 FastAPI 的 `HTTPBearer` / `OAuth2PasswordBearer` 提取 Bearer token
   - 实现 5 步验证:
     1. 提取 Bearer token
     2. 用 JWT_SECRET 验证签名 (HS256)
     3. 检查 exp 是否过期
     4. 解析 payload 中的 `sub` (userId)，查询数据库确认用户存在
     5. 将 User 对象注入到 `current_user` 参数
   - 返回 User 模型实例
2. **错误处理**:
   - Token 缺失 / 格式错误 → `TokenInvalidError("Token 无效")`
   - JWT 验签失败 / 过期 → `TokenInvalidError("Token 已过期")`
   - 用户不存在 / 被删除 → `TokenInvalidError("用户不存在")`
   - 用户 status='locked' → 检查 `locked_until` 是否过期
     - 已过期 → 自动解锁 (status='active', failed_login_count=0)，放行
     - 未过期 → `AccountLockedError`
3. **注意**: 不在此层处理 rate limit（由 Task 04 的中间件负责）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 02 User 模型可导入并使用
- [ ] Task 03 TokenInvalidError, AccountLockedError 可用
- [ ] 数据库中有测试用户

### 功能验收
- [ ] 有效 Token → `get_current_user` 返回 User 对象（含 id, username, status）
- [ ] 无效 Token（篡改签名）→ 抛出 TokenInvalidError, HTTP 401
- [ ] 已过期 Token → 抛出 TokenInvalidError, HTTP 401
- [ ] Authorization header 缺失 → 抛出 TokenInvalidError, HTTP 401
- [ ] locked 用户且 locked_until 已过期 → 自动解锁并返回 User
- [ ] locked 用户且 locked_until 未过期 → 抛出 AccountLockedError, HTTP 423

### AC 验收
- [ ] AC-AUTH-010: 篡改/过期的 Token 访问认证端点 → HTTP 401 TOKEN_INVALID

### 代码质量
- [ ] Token 解析使用 python-jose 库（与 Task 08 的 JWT 工具函数共用同一密钥和算法）
- [ ] 数据库查询使用 async session
- [ ] 不在此中间件中做 rate limiting

### 通过判定
全部 ✅ → 任务 Done，进入 Task 06
