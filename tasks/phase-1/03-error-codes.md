# Task 03: 统一错误码体系

## 对应 Spec
- specs/auth/03-api-contract.md（全部 Error Responses 表格）
- specs/research/03-api-contract.md（全部 Error Responses 表格）

## 输入文件（Agent 需读取）
- specs/auth/03-api-contract.md（Error Responses 汇总）
- specs/research/03-api-contract.md（Error Responses 汇总）
- src/main.py（FastAPI app 创建）

## 输出文件
- `src/errors.py`（异常类定义 + FastAPI exception handler）

## 前置任务
- Task 01（项目骨架，FastAPI app 已创建）

## 实现要求
1. **AppException 基类**:
   - 字段: `http_status: int`, `code: str`, `message: str`
   - 继承自 `Exception`
2. **子类异常** (每个 code 一个类):
   - `InvalidCredentialsError(401, "INVALID_CREDENTIALS")`
   - `TokenInvalidError(401, "TOKEN_INVALID")`
   - `AccountLockedError(423, "ACCOUNT_LOCKED")`
   - `UsernameExistsError(409, "USERNAME_EXISTS")`
   - `InvalidUsernameError(400, "INVALID_USERNAME")`
   - `InvalidPasswordError(400, "INVALID_PASSWORD")`
   - `RateLimitedError(429, "RATE_LIMITED")`
   - `NotFoundError(404, "NOT_FOUND")`
   - `ForbiddenError(403, "FORBIDDEN")`
   - `InvalidStatusError(400, "INVALID_STATUS")`
   - `ResearchInProgressError(409, "RESEARCH_IN_PROGRESS")`
   - `TooManyRevisionsError(400, "TOO_MANY_REVISIONS")`
   - `ReportNotReadyError(400, "REPORT_NOT_READY")`
   - `PlanGenerationFailedError(500, "PLAN_GENERATION_FAILED")`
- `PlanGenerationTimeoutError(504, "PLAN_GENERATION_TIMEOUT")`
- `InvalidTopicError(400, "INVALID_TOPIC")`
- `InvalidTemplateError(400, "INVALID_TEMPLATE")`
- `ServiceUnavailableError(503, "SERVICE_UNAVAILABLE")`
3. **FastAPI Exception Handler**:
   - 捕获 `AppException` 及其子类
   - 返回统一格式: `{"code": "...", "message": "..."}`
   - HTTP 状态码由异常实例的 `http_status` 决定
4. **注册到 FastAPI app**:
   - 在 `main.py` 的 `create_app()` 中 `app.add_exception_handler(AppException, app_exception_handler)`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 01 产出文件 `src/main.py` 存在
- [ ] FastAPI app 可正常导入

### 功能验收
- [ ] 所有 16 个错误码均定义了对应的异常类
- [ ] 抛出 `UsernameExistsError("该账号已被注册")` → FastAPI 返回 `{"code": "USERNAME_EXISTS", "message": "该账号已被注册"}`, HTTP 409
- [ ] 抛出 `TokenInvalidError("Token 已过期")` → FastAPI 返回 `{"code": "TOKEN_INVALID", "message": "Token 已过期"}`, HTTP 401
- [ ] 所有异常类的 `code` 与对应 spec 的 API 文档中 Error Responses 表格一致

### 代码质量
- [ ] 异常类不包含硬编码的中文 message（message 通过参数传入）
- [ ] `http_status` 与 code 语义匹配（如 401=认证失败, 409=冲突, 423=锁定）
- [ ] 无重复 code 值

### Spec 一致性
- [ ] Auth 模块 spec 中的 7 个不同 code 已覆盖
- [ ] Research 模块 spec 中的 9 个不同 code 已覆盖
- [ ] 错误响应 JSON 格式与 spec 一致: `{"code": "...", "message": "..."}`

### 通过判定
全部 ✅ → 任务 Done，进入 Task 04
