# Task 11: 登录接口 — 测试 (TDD: RED)

> **TDD 模式**: 本任务仅生成测试文件。由于业务代码尚未实现，测试执行后应全部 **RED**。

## 对应 Spec
- specs/auth/03-api-contract.md API-AUTH-002
- specs/auth/06-acceptance.md AC-AUTH-004, 005, 006, 007, 008, 009, 012
- specs/auth/05-edge-cases.md EC-AUTH-003, 004, 008

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md API-AUTH-002（请求/响应格式 + 错误码）
- specs/auth/06-acceptance.md（AC-AUTH-004 ~ 009, 012）
- specs/auth/04-business-rules.md RULE-AUTH-002, 003, 004
- tests/conftest.py

## 输出文件
- `tests/auth/test_login.py`

## 前置任务
- Task 10（register 已实现，可创建测试用户）
- Task 04（rate limiter 可用）

## 实现要求
1. **测试数据隔离**: 每个测试用例使用 `beforeEach` 创建自己需要的测试用户（通过 register API），`afterEach` 清理。

2. **测试用例清单**:

| 测试用例 | 覆盖 AC | 描述 |
|---|---|---|
| `test_login_success` | AC-AUTH-004 | 正确凭据 → 200, JWT, expiresIn=86400, failed_login_count=0 |
| `test_login_remember_me` | AC-AUTH-005 | rememberMe=true → expiresIn=604800 |
| `test_login_wrong_password` | AC-AUTH-006 | 错误密码 → 401, failed_login_count+1 |
| `test_login_nonexistent_user` | — | 不存在的用户 → 401 INVALID_CREDENTIALS（不泄露用户是否存在） |
| `test_login_account_locked_after_5_fail` | AC-AUTH-007 | 连续5次错误 → 第6次（即使是正确密码）→ 423 ACCOUNT_LOCKED |
| `test_login_correct_password_while_locked` | AC-AUTH-008 | locked + 未过期 + 正确密码 → 423 ACCOUNT_LOCKED |
| `test_login_auto_unlock_after_expiry` | AC-AUTH-009 | locked_until 已过期 + 正确密码 → 200（自动解锁） |
| `test_login_rate_limit` | AC-AUTH-012 | 连续 POST /login > 10次/分钟 → 429 RATE_LIMITED |
| `test_login_empty_username` | — | username="" → 400 校验失败 |
| `test_login_empty_password` | — | password="" → 400 校验失败 |
| `test_login_username_case_insensitive` | — | 注册 "User" → 用 "user" 登录 → 成功 |

3. **测试结构示例**:
   ```python
   @pytest.mark.asyncio
   async def test_login_success(async_client):
       # Setup: 先注册测试用户
       await async_client.post("/api/v1/auth/register", json={
           "username": "logintest", "password": "TestPass1"
       })
       
       # Action
       response = await async_client.post("/api/v1/auth/login", json={
           "username": "logintest", "password": "TestPass1"
       })
       
       # Assert
       assert response.status_code == 200
       data = response.json()
       assert data["username"] == "logintest"
       assert data["expiresIn"] == 86400
       
       # Cleanup: 从数据库删除测试用户
   ```

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 10 register 接口已在容器内可用（curl 可验证）
- [ ] Task 04 rate limiter 中间件已注册
- [ ] 测试数据库已隔离（每条测试可独立 create/delete 用户）

### AC 验收
- [ ] 所有测试用例覆盖 AC-AUTH-004 ~ 009, 012（共 7 个 AC）
- [ ] 执行 `pytest tests/ -k test_login -v` → 全部 RED（业务代码未实现）

### 测试隔离验证
- [ ] 每个测试用例通过 register API 创建自己的测试用户
- [ ] 测试之间无数据污染（清理逻辑完整）
- [ ] 不依赖 Task 09 的测试数据

### 通过判定
全部 ✅ → 任务状态标记为 🔴 **RED** → 进入 Task 12（实现）
