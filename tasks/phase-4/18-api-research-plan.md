# Task 18: 研究计划 — 实现 (TDD: GREEN)

> **TDD 模式**: 完成后必须运行 Task 17 的测试用例，全部 **GREEN**。**禁止修改 Task 17 的测试文件。**

## 对应 Spec
- specs/research/03-api-contract.md: API-RES-001, 002, 003, 005
- specs/research/06-acceptance.md: AC-RES-001, 002, 003, 004, 005, 006, 019, 022, 023
- specs/research/04-business-rules.md: RULE-RES-001, 002, 003, 004

## 输入文件（Agent 需读取）
- tasks/phase-4/17-test-research-plan.md（测试用例，不可修改）
- src/services/llm_service.py（generate_plan, revise_plan）
- src/repos/research_repo.py（ResearchRepository）
- src/repos/plan_feedback_repo.py（ResearchPlanFeedbackRepository）
- src/repos/sub_agent_result_repo.py（SubAgentResultRepository）
- src/middleware/auth.py（get_current_user）
- src/errors.py
- src/models/research.py

## 输出文件
- `src/api/research/__init__.py`
- `src/api/research/router.py`（4 个路由: new, revise, confirm, get）
- `src/api/research/schemas.py`（NewResearchRequest, ReviseRequest, ResearchResponse 等 Pydantic Schema）
- `src/api/research/service_plan.py`（研究计划业务逻辑）
- 在 `src/api/router.py` 中注册 research 子路由

## 前置任务
- Task 14（Research model/repo 可用）
- Task 15（LLM 服务可用）
- Task 05（auth middleware 可用）
- Task 04（rate limiter 可用）
- Task 17（测试用例已写好，当前全 RED）

## 实现要求

### 1. POST `/api/v1/research/new` (API-RES-001)
```
1. Auth + Rate limit check
2. Pydantic validation: topic (1-500), template (enum)
3. 检查用户是否有进行中 research (status IN ('running'))
   → 409 RESEARCH_IN_PROGRESS
   注意: 'confirmed' 为瞬态不持久化，无需检查；draft 不阻塞（用户可有多条草稿）
4. 调用 llm_service.generate_plan(topic, template)
   → 30 秒超时 → 500 PLAN_GENERATION_FAILED
5. 创建 Research(status='draft', plan_json=plan, template, topic)
6. 创建对应的 SubAgentResult 记录 (status='pending') — 按 plan.subAgents 逐条创建
7. 返回 201: { researchId, plan: {subAgents}, planRound: 1 }
```

### 2. POST `/api/v1/research/{id}/plan/revise` (API-RES-002) — **同步**
```
1. Auth + Rate limit
2. 查找 Research → 404 / 403
3. status != 'draft' → 400 INVALID_STATUS
4. 修改轮次 ≥ 10 → 400 TOO_MANY_REVISIONS
5. 调用 llm_service.revise_plan(topic, current_plan, feedback)
   → 30 秒超时 → 504 PLAN_GENERATION_TIMEOUT
6. **删除旧的 SubAgentResult 记录**（通过 SubAgentResultRepository 批量删除 research_id 关联的全部记录）
7. 更新 plan_json, **创建新 SubAgentResult 记录** (status='pending') 以匹配更新后的计划
8. 保存 ResearchPlanFeedback(round, feedback, plan_snapshot)
9. 返回 200: { plan: {subAgents}, planRound }
```

### 3. POST `/api/v1/research/{id}/plan/confirm` (API-RES-003)
```
1. Auth
2. 查找 Research → 404 / 403
3. status != 'draft' → 400 INVALID_STATUS
4. status → 'running', started_at = now()
5. 后台异步触发研究执行 (调用 Task 19 的执行引擎)
6. 返回 200: { researchId, status: "running", streamUrl }
```

### 4. GET `/api/v1/research/{id}` (API-RES-005)
```
1. Auth
2. 查找 Research → 404 (deleted_at NULL)
3. 权限检查 → 403
4. 返回完整 Research 对象 (plan, subAgentResults, feedbacks 等)
5. 按 status 返回不同字段集
```

### 5. Pydantic Schemas:
```python
class NewResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    template: ResearchTemplateEnum

class ReviseRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=1000)

class ResearchResponse(BaseModel):
    researchId: UUID
    topic: str
    template: str
    status: str
    plan: dict | None
    planRound: int
    subAgentResults: list
    totalTokens: int
    # ... 时间字段
```

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 14, 15, 05 均已完成
- [ ] Task 17 测试文件存在且未被修改

### AC 验收
- [ ] AC-RES-001: POST /new → 201, 3-5 Sub-agents, status='draft'
- [ ] AC-RES-002: 已有进行中研究 → 409
- [ ] AC-RES-019: LLM 超时 → 500, status 保持 draft, 可重试
- [ ] AC-RES-005: POST /confirm → 200, status='running', streamUrl 正确, started_at 已设置
- [ ] AC-RES-003: POST /revise → planRound 递增, 保存 feedback
- [ ] AC-RES-004: 第 11 次 revise → 400 TOO_MANY_REVISIONS
- [ ] AC-RES-006: GET /{id} draft → 可获取并恢复
- [ ] AC-RES-022: GET /{id} draft → plan + planRound 完整
- [ ] AC-RES-023: GET /{id} running → subAgentResults 含已完成结果

### TDD 验证
- [ ] `pytest tests/ -k test_plan -v` → 全部 PASS
- [ ] 未修改 Task 17 的测试文件

### 代码质量
- [ ] LLM 调用在 service 层，router 层只做路由和参数校验
- [ ] 事务管理: plan 生成失败时数据库不残留脏数据
- [ ] 权限检查: 每个接口验证 research.user_id == current_user.id

### 通过判定
全部 ✅ → 任务 Done，进入 Task 19
