# Task 15: LLM 服务封装

## 对应 Spec
- specs/research/04-business-rules.md:
  - RULE-RES-002（模板拆分策略 — 决定 plan generation prompt）
  - RULE-RES-003（计划修改轮次限制 — revise prompt 受此约束）
  - RULE-RES-005（Sub-agent 搜索循环 — 决定 search prompt 逻辑）
  - RULE-RES-008（汇总 Agent 策略 — 决定 aggregate prompt 结构）
- docs/tech-decision.md §决策5 (LiteLLM)

## 输入文件（Agent 需读取）
- specs/research/04-business-rules.md（RULE-RES-002, 003, 005, 008）
- docs/tech-decision.md §决策5
- docs/research-report.md §模块5 (LiteLLM)
- src/config.py（LLM_API_KEY, LLM_BASE_URL, LLM_MODEL）

## 输出文件
- `src/services/__init__.py`
- `src/services/llm_service.py`（LLM 服务封装）
- `src/services/prompts.py`（Prompt 模板）

## 前置任务
- Task 01（config.py 中 LLM 配置可用）

## 实现要求

### 1. LLM 服务 (`src/services/llm_service.py`):
- 使用 LiteLLM 的 `acompletion()` API
- 配置: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (default: "gpt-4o")
- 超时: 30 秒（所有 LLM 调用）
- 方法:
  - `async def generate_plan(topic, template, db: Session) -> list[dict]`:
    - 输入: 研究主题 + 模板类型
    - 输出: `[{name, goal, searchDirection}, ...]` (3-5 个)
    - 使用 `PLAN_GENERATION_PROMPT`
  - `async def revise_plan(topic, current_plan, feedback, db: Session) -> list[dict]`:
    - 输入: 主题 + 当前计划 + 用户反馈
    - 输出: 更新后的 Sub-agent 列表
  - `async def aggregate_report(topic, plan, sub_agent_results, db: Session) -> str`:
    - 输入: 主题 + 计划 + Sub-agent 完成结果
    - 输出: Markdown 报告字符串（≤50000 字符）
  - `async def sub_agent_search(findings, search_results, direction, db: Session) -> str`:
    - 输入: 当前发现 + 新搜索结果 + 搜索方向
    - 输出: 更新后的 findings Markdown 文本

### 2. Prompt 模板 (`src/services/prompts.py`):
- `PLAN_GENERATION_PROMPT`: 根据 topic + template 生成 Sub-agent 计划
- `PLAN_REVISION_PROMPT`: 根据用户反馈修改计划
- `SUB_AGENT_SEARCH_PROMPT`: Sub-agent 分析搜索结果并产生发现
- `AGGREGATE_PROMPT`: 汇总所有 Sub-agent 结果成 Markdown 报告

### 3. 日志与指标:
- 每次 LLM 调用记录: prompt 长度、completion 长度、耗时、token 消耗
- 超时 → 日志 WARNING 并抛出 PlanGenerationTimeoutError

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 01 config.py 中 LLM_API_KEY 和 LLM_BASE_URL 已配置
- [ ] 容器环境可访问 LLM API endpoint

### 功能验收
- [ ] `generate_plan("React 19 新特性", "tech_research")` → 返回 3-5 个 Sub-agent
- [ ] 每个 Sub-agent 含 name, goal, searchDirection 三个字段
- [ ] `revise_plan(...)` → 返回修改后的计划（与用户反馈对应）
- [ ] `aggregate_report(...)` → 返回 Markdown 格式文本
- [ ] 每次 LLM 调用有日志（prompt_len, response_len, duration_ms）

### 代码质量
- [ ] 所有 LLM 调用使用 `try/except` 处理超时和 API 错误
- [ ] Prompt 模板可维护（字符串常量或单独文件，不在 service 中硬编码）
- [ ] LLM 响应解析有容错（返回格式不符合预期时回退处理）
- [ ] Token 消耗可提取（从 LiteLLM response 的 usage 字段）

### Spec 一致性
- [ ] RULE-RES-001: 计划生成 Prompt 包含模板相关约束
- [ ] RULE-RES-002: 修改计划 Prompt 包含当前计划上下文
- [ ] RULE-RES-007: 汇总 Prompt 要求输出 Markdown 格式

### 通过判定
全部 ✅ → 任务 Done，进入 Task 16
