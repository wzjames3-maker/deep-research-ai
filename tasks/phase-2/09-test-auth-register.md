# Task 09: 注册接口 — 测试 (TDD: RED)

> **TDD 模式**: 本任务仅生成测试文件。由于业务代码尚未实现，测试执行后应全部 **RED**（失败）。

## 对应 Spec
- specs/auth/03-api-contract.md API-AUTH-001
- specs/auth/06-acceptance.md AC-AUTH-001, 002, 003, 011

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md API-AUTH-001（请求/响应格式 + 错误码）
- specs/auth/06-acceptance.md（AC-AUTH-001, 002, 003, 011）
- specs/auth/04-business-rules.md RULE-AUTH-001, RULE-AUTH-005, RULE-AUTH-006
- specs/auth/05-edge-cases.md EC-AUTH-001
- src/errors.py（错误码类）
- tests/conftest.py（测试基础设施）

## 输出文件
- `tests/auth/test_register.py`（测试用例，不含业务实现）
  - 或 `tests/test_auth_register.py`（根据 conftest 约定的命名）

## 前置任务
- Task 01（测试基础设施 conftest.py）
- Task 02（User 表已创建）
- Task 03（错误码异常类可用）

## 实现要求
1. **测试用例必须包含完整的数据隔离**:
   - 每个测试 `beforeEach/afterEach` 清理自己创建的数据
   - 使用 `@pytest.fixture(autouse=True)` 或 `setup/teardown`

2. **测试用例清单**:

| 测试用例 | 覆盖 AC | 描述 |
|---|---|---|
| `test_register_success` | AC-AUTH-001 | 正常注册 → 201 + JWT + lowercase username |
| `test_register_weak_password` | AC-AUTH-002 | 密码 "1234" → 400 INVALID_PASSWORD |
| `test_register_short_username` | AC-AUTH-002 | 用户名 "ab" → 400 INVALID_USERNAME |
| `test_register_invalid_username_chars` | — | 用户名含特殊字符 → 400 INVALID_USERNAME |
| `test_register_duplicate_case_insensitive` | AC-AUTH-003 | 已存在 "dupe"，注册 "Dupe" → 409 USERNAME_EXISTS |
| `test_register_duplicate_exact` | AC-AUTH-003 | 已存在 "dupe"，注册 "dupe" → 409 USERNAME_EXISTS |
| `test_register_trim_and_lowercase` | AC-AUTH-001 | 输入 " ZhangSan " → username = "zhangsan" |
| `test_register_case_insensitive_login_hint` | AC-AUTH-011 | 注册 "ZHANGSAN" 后，检查 username 存储为 "zhangsan" |

3. **测试结构**:
   ```python
   @pytest.mark.asyncio
   async def test_register_success(async_client):
       # 清理: 确保测试用户不存在
       # ...
       
       response = await async_client.post("/api/v1/auth/register", json={
           "username": "newuser",
           "password": "StrongPass1"
       })
       
       assert response.status_code == 201
       data = response.json()
       assert "userId" in data
       assert data["username"] == "newuser"
       assert len(data["token"].split(".")) == 3  # JWT 3 segments
       assert data["expiresIn"] == 86400
   ```

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 02 DB Migration 已执行，User 表存在
- [ ] Task 03 错误码类已可用
- [ ] `tests/conftest.py` 提供 `async_client` fixture
- [ ] 测试数据库与开发数据库隔离（独立 DB 或独立 schema）

### AC 验收
- [ ] 所有测试用例均覆盖对应的 AC-AUTH-001, 002, 003, 011
- [ ] 执行 `pytest tests/ -k test_register -v` → 全部 RED（业务代码未实现）
- [ ] 失败的 assertion 信息明确（非 "assert 500" 这种无意义错误）

### 测试隔离验证
- [ ] 每个测试用例有独立的 setup（不依赖其他用例创建的用户）
- [ ] 测试之间无共享可变状态
- [ ] 实现了清理逻辑（teardown 删除测试用户或使用事务回滚）

### 通过判定
全部 ✅ → 任务状态标记为 🔴 **RED** → 进入 Task 10（实现）
