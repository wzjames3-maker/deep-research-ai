# Task 07: Auth 数据模型与 Repository

## 对应 Spec
- specs/auth/02-data-model.md（User 表字段）
- specs/auth/04-business-rules.md RULE-AUTH-003（锁定逻辑）, RULE-AUTH-005（大小写不敏感）

## 输入文件（Agent 需读取）
- specs/auth/02-data-model.md
- specs/auth/04-business-rules.md（RULE-AUTH-003, RULE-AUTH-005）
- src/models/base.py（Base + get_db）
- src/models/user.py（User 模型骨架，Task 02 产出）

## 输出文件
- `src/models/user.py`（增强 User 模型：添加方法）
- `src/repos/__init__.py`
- `src/repos/user_repo.py`（UserRepository）

## 前置任务
- Task 02（DB Migration，User 表已创建）
- Task 05（get_db 可用）

## 实现要求
1. **User 模型增强**:
   - `clean_username(cls, username)` classmethod: strip + lowercase
   - `increment_failed_login()`: `failed_login_count += 1`; 若 ≥ 5 → `status='locked'`, `locked_until = now + 15min`
   - `reset_failed_login()`: `failed_login_count = 0`
   - `check_and_auto_unlock()`: 若 `locked_until` 已过期 `(locked_until < now)` → 自动解锁 + 重置计数
   - `to_dict()`: 返回 dict（不含 password_hash）
2. **UserRepository**:
   - `create(username: str, password_hash: str) -> User`: INSERT 新用户
   - `find_by_id(user_id: UUID) -> Optional[User]`: 按 ID 查询
   - `find_by_username(username: str) -> Optional[User]`: 按 username（lowercase）查询
   - `exists_by_username(username: str) -> bool`: 检查用户名是否已存在
   - `save(user: User) -> None`: flush 变更到 DB

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 02 DB Migration 已执行，User 表存在
- [ ] `get_db` async generator 可用

### 功能验收
- [ ] `clean_username(" ZhangSan ")` → `"zhangsan"`
- [ ] `create("test", "hash")` → 插入成功，username 存储在数据库中为 "test"
- [ ] 连续 5 次 `increment_failed_login()` → status='locked', locked_until 非空
- [ ] `check_and_auto_unlock()` 对过期的 locked_until → 解锁成功
- [ ] `find_by_username("TeSt")` → 查找 "test" 返回用户（大小写不敏感）

### AC 验收
- [ ] AC-AUTH-003: 重复注册时 `exists_by_username` 返回 True（大小写不敏感）
- [ ] AC-AUTH-011: 注册 "ZHANGSAN" → 登录 "zhangsan" 成功

### 代码质量
- [ ] 所有 DB 操作使用 async/await
- [ ] `find_by_username` 使用 `func.lower(User.username) == username.lower()` 确保大小写不敏感
- [ ] 无 SQL 注入风险（使用 SQLAlchemy ORM）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 08
