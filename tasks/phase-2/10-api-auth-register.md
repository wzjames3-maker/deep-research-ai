# Task 10: 注册接口 — 实现 (TDD: GREEN)

> **TDD 模式**: 本任务实现业务代码。完成后必须运行 Task 09 的测试用例，且必须全部 **GREEN**（通过）。**禁止修改 Task 09 生成的测试文件。**

## 对应 Spec
- specs/auth/03-api-contract.md API-AUTH-001
- specs/auth/06-acceptance.md AC-AUTH-001, 002, 003, 011

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md API-AUTH-001
- specs/auth/04-business-rules.md RULE-AUTH-001, RULE-AUTH-005, RULE-AUTH-006
- specs/auth/05-edge-cases.md EC-AUTH-001
- tasks/phase-2/09-test-auth-register.md（测试用例，不可修改）
- src/models/user.py（User 模型 + Repository，Task 07）
- src/utils/bcrypt.py（bcrypt 工具，Task 08）
- src/utils/jwt.py（JWT 工具，Task 08）
- src/errors.py（错误码类，Task 03）
- src/middleware/rate_limiter.py（速率限制，Task 04）

## 输出文件
- `src/api/auth/__init__.py`
- `src/api/auth/router.py`（仅含 POST /register）
- `src/api/auth/schemas.py`（RegisterRequest, RegisterResponse pydantic 模型）
- `src/api/auth/service.py`（register_user 业务逻辑）
- 在 `src/api/router.py` 中注册 auth 子路由

## 前置任务
- Task 07（UserRepository 可用）
- Task 08（bcrypt + JWT 工具可用）
- Task 04（Rate limiter 可用）
- Task 09（测试用例已写好，当前应全 RED）

## 实现要求
1. **严格按 API-AUTH-001 实现**:
   - POST `/api/v1/auth/register`
   - Body: `{ "username": "str", "password": "str" }`
   - Success: 201 `{ "userId": "uuid", "username": "str", "token": "str", "expiresIn": 86400 }`
   - Error codes: 400 INVALID_USERNAME, 400 INVALID_PASSWORD, 409 USERNAME_EXISTS, 429 RATE_LIMITED
   - **并发安全 (EC-AUTH-001)**: 禁止先 SELECT 再 INSERT；应直接 INSERT 并捕获 IntegrityError → 转为 409

2. **业务逻辑流程**:
   ```
   1. Rate limit check (5/分钟/IP)
   2. Pydantic schema validation:
      - username: 3-50 chars, 仅 [a-zA-Z0-9_]
      - password: 8-64 chars, 至少 1 个字母 + 1 个数字
   3. clean_username: strip + lowercase
   4. 检查 username 是否存在 → 409 USERNAME_EXISTS
   5. bcrypt hash password (cost=12)
   6. UserRepository.create(username_clean, password_hash)
   7. JWT create_token(user.id, user.username)
   8. 返回 201
   ```

3. **Pydantic schema**:
   ```python
   class RegisterRequest(BaseModel):
       username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
       password: str = Field(min_length=8, max_length=64)
       # password 需额外验证器: 至少1字母+1数字

   class RegisterResponse(BaseModel):
       userId: UUID
       username: str
       token: str
       expiresIn: int
   ```

4. **完成后必须**:
   - 运行 `pytest tests/ -k test_register -v` → 全部 GREEN
   - Task 09 的所有 8 个测试用例必须通过

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 07 UserRepository 验证通过（模型 + repo 可用）
- [ ] Task 08 工具函数 verify_password/create_token 验证通过
- [ ] Task 09 测试用例文件存在且未被修改
- [ ] 以下命令均在容器内执行

### AC 验收
- [ ] AC-AUTH-001: POST /auth/register → 201, JWT 3 段, username lowercase, expiresIn=86400
- [ ] AC-AUTH-002: password "1234" → 400 INVALID_PASSWORD
- [ ] AC-AUTH-003: 已存在 "dupe" → 409 USERNAME_EXISTS
- [ ] AC-AUTH-011: 注册 "ZHANGSAN" → username 存储为 "zhangsan"

### TDD 验证
- [ ] `pytest tests/ -k test_register -v` → 全部 PASS（0 failed）
- [ ] 未修改 Task 09 生成的测试文件（通过 git diff 验证）

### 代码质量
- [ ] 入参使用 Pydantic schema 校验（非手动正则）
- [ ] bcrypt hash 在服务层生成（非中间件）
- [ ] 错误信息不含敏感信息
- [ ] Service 层使用 async/await + DI（Depends）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 11
