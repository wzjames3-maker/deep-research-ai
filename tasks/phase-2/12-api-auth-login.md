# Task 12: 登录接口 — 实现 (TDD: GREEN)

> **TDD 模式**: 完成后必须运行 Task 11 的测试用例，全部 **GREEN**。**禁止修改 Task 11 生成的测试文件。**

## 对应 Spec
- specs/auth/03-api-contract.md API-AUTH-002
- specs/auth/06-acceptance.md AC-AUTH-004, 005, 006, 007, 008, 009, 012
- specs/auth/04-business-rules.md RULE-AUTH-002, 003, 004
- specs/auth/05-edge-cases.md EC-AUTH-003, 004, 008

## 输入文件（Agent 需读取）
- tasks/phase-2/11-test-auth-login.md（测试用例，不可修改）
- src/repos/user_repo.py（UserRepository）
- src/utils/bcrypt.py（verify_password）
- src/utils/jwt.py（create_token）
- src/errors.py
- src/api/auth/schemas.py（添加 LoginRequest, LoginResponse）
- src/api/auth/service.py（已有 register，追加 login）

## 输出文件
- `src/api/auth/schemas.py`（追加 LoginRequest, LoginResponse）
- `src/api/auth/service.py`（追加 `login_user` 函数）
- `src/api/auth/router.py`（追加 POST /login 路由）

## 前置任务
- Task 10（register 已实现）
- Task 07（UserRepository 可用）
- Task 08（bcrypt + JWT 工具可用）
- Task 04（rate limiter 可用）
- Task 11（测试用例已写好，当前应全 RED）

## 实现要求
1. **严格按 API-AUTH-002 实现**:
   ```
   POST /api/v1/auth/login
   Body: { "username": "str", "password": "str", "rememberMe": "bool (optional)" }
   Success: 200 { "userId": "uuid", "username": "str", "token": "str", "expiresIn": 86400 }
   Errors: 401 INVALID_CREDENTIALS, 423 ACCOUNT_LOCKED, 429 RATE_LIMITED
   ```

2. **业务逻辑流程**:
   ```
   1. Rate limit check (10/分钟/IP)
   2. Pydantic validation
   3. 查找用户 (by username, case-insensitive via UserRepository)
   4. 用户不存在 → 返回 401 INVALID_CREDENTIALS（不区分"用户不存在"和"密码错误"）
   5. 检查用户 status 是否 locked:
      a. locked_until 已过期 → 自动解锁 (status='active', failed_login_count=0)
      b. locked_until 未过期 → 返回 423 ACCOUNT_LOCKED
   6. 验证密码:
      a. 正确 → reset_failed_login() + 生成 JWT + 返回 200
      b. 错误 → increment_failed_login()
         - 若 failed_login_count 达到 5 → 自动锁定 15 分钟
         - 返回 401 INVALID_CREDENTIALS
   7. rememberMe=true → JWT expiresIn = 604800 (7天)
   ```

3. **Pydantic Schema**:
   ```python
   class LoginRequest(BaseModel):
       username: str = Field(min_length=1)
       password: str = Field(min_length=1)
       rememberMe: bool = Field(default=False)

   class LoginResponse(BaseModel):
       userId: UUID
       username: str
       token: str
       expiresIn: int
   ```

4. **安全要求**:
   - 密码错误和用户不存在返回相同的 401 错误（防止用户名枚举攻击）
   - 失败次数增加后立即检查是否达到锁定阈值
   - 锁定时间使用 UTC 时间戳

5. **完成后必须**:
   - 运行 `pytest tests/ -k test_login -v` → 全部 GREEN

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 10 register 已可通过 curl 验证
- [ ] Task 07 UserRepository 的 increment/reset_failed_login 已实现
- [ ] Task 11 测试文件存在且未被修改

### AC 验收
- [ ] AC-AUTH-004: 正确登录 → 200, expiresIn=86400, failed_login_count 归零
- [ ] AC-AUTH-005: rememberMe=true → expiresIn=604800
- [ ] AC-AUTH-006: 错误密码 → 401, failed_login_count+1
- [ ] AC-AUTH-007: 5 次错误 → locked + 正确密码返回 423
- [ ] AC-AUTH-008: locked + 未过期 → 正确密码返回 423
- [ ] AC-AUTH-009: locked + 已过期 → 自动解锁并登录成功
- [ ] AC-AUTH-012: >10 次/分钟 → 429 RATE_LIMITED

### TDD 验证
- [ ] `pytest tests/ -k test_login -v` → 全部 PASS
- [ ] 未修改 Task 11 生成的测试文件

### 代码质量
- [ ] 用户不存在和密码错误返回相同的错误 code/message（防枚举）
- [ ] 锁定逻辑使用 UTC 时间
- [ ] 错误信息不含用户具体状态（如不暴露 "user is locked" 内部细节）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 13
