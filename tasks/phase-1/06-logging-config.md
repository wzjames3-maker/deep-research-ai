# Task 06: 结构化日志配置

## 对应 Spec
- docs/tech-decision.md（日志策略）

## 输入文件（Agent 需读取）
- src/main.py（FastAPI app 创建）
- src/config.py（LOG_LEVEL 等配置）

## 输出文件
- `src/utils/logging.py`（结构化日志配置）

## 前置任务
- Task 01（项目骨架）

## 实现要求
1. **日志库**: `structlog`（与 Python logging 集成）
2. **格式**: JSON（生产环境），Console（开发环境）
3. **必需字段**（每条日志自动包含）:
   - `timestamp`: ISO8601
   - `level`: INFO/WARNING/ERROR/DEBUG
   - `service`: "deepresearch"
   - `request_id`: 从中间件注入的 UUID（追踪同一次 HTTP 请求的所有日志）
4. **日志级别**:
   - LLM 调用: INFO（记录 prompt 长度、response 长度、耗时）
   - MCP 搜索: INFO（记录搜索词、返回结果数量）
   - HTTP 请求: INFO（status, method, path, duration）
   - Sub-agent 状态变更: INFO
   - 异常: ERROR（含完整 traceback）
5. **中间件**:
   - `RequestIdMiddleware`: 注入 `X-Request-ID` header（或生成 UUID），存储在 `contextvars`
6. **敏感信息过滤**:
   - 不记录 password、password_hash、token、ticket 的完整值
   - 不记录 LLM API key

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 01 的 FastAPI app 可运行

### 功能验收
- [ ] 每个 HTTP 请求自动注入 request_id，日志包含该 ID
- [ ] `/health` 端点日志包含 method=GET, path=/health, status=200, duration
- [ ] 模拟异常 → 日志级别=ERROR，含 traceback
- [ ] 日志输出为 JSON 格式（生产模式 `LOG_FORMAT=json`）

### 代码质量
- [ ] request_id 使用 `contextvars` 在线程/协程间传播
- [ ] 日志中不含 password/token/api_key 完整明文
- [ ] structlog 配置不覆盖 Python 标准库的 logging 处理器

### 通过判定
全部 ✅ → 任务 Done，进入 Phase 2 (Task 07)
