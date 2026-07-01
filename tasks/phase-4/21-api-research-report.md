# Task 21: 研究报告接口

## 对应 Spec
- specs/research/03-api-contract.md API-RES-006 (GET /report)
- specs/research/06-acceptance.md AC-RES-014, 016, 020
- specs/research/04-business-rules.md RULE-RES-007（汇总规则）, RULE-RES-010（软删除）

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md API-RES-006
- specs/research/06-acceptance.md AC-RES-014, 016, 020
- src/repos/research_repo.py
- src/middleware/auth.py
- src/errors.py

## 输出文件
- `src/api/research/router.py`（追加 GET /report）
- `src/api/research/schemas.py`（追加 ReportResponse Schema）

## 前置任务
- Task 19（执行引擎已生成 report_markdown 数据）
- Task 14（Research model/repo 可用）

## 实现要求

### GET `/api/v1/research/{id}/report` (API-RES-006):
```
1. Auth
2. 查找 Research (deleted_at IS NULL) → 404
3. 权限检查 → 403
4. status != 'completed' → 400 REPORT_NOT_READY
5. 返回完整报告:
   - researchId, topic, template, status, totalTokens
   - plan.subAgents
   - reportMarkdown
   - subAgentResults: 每个含 name, goal, status, findings, visitedUrls, tokenUsed
   - 时间戳
```

### Pydantic Schema:
```python
class SubAgentResultItem(BaseModel):
    name: str
    goal: str
    status: str
    findings: str
    visitedUrls: list[str]
    tokenUsed: int

class ReportResponse(BaseModel):
    researchId: UUID
    topic: str
    template: str
    status: str
    plan: dict
    reportMarkdown: str | None
    subAgentResults: list[SubAgentResultItem]
    totalTokens: int
    createdAt: datetime
    completedAt: datetime | None
```

### 附加: `GET /api/v1/research/{id}/report/render` (可选)
- 如果前端想直接渲染 Markdown → 用此端点返回纯 Markdown 文本 + Content-Type: text/markdown
- V1 可选，前端可直接从 report 接口取 reportMarkdown

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 19 已完成，至少有一条 status='completed' 的研究记录
- [ ] Research 表中有 report_markdown 数据

### AC 验收
- [ ] AC-RES-014: GET /report → 200, reportMarkdown 非空, subAgentResults 完整
- [ ] AC-RES-016: totalTokens = SUM(sub_agent_results.token_used)
- [ ] AC-RES-020: 报告 > 50000 字符 → 截断 + 提示

### 功能验收
- [ ] status='draft' → 400 REPORT_NOT_READY
- [ ] status='failed' → 400 REPORT_NOT_READY
- [ ] 软删除研究 GET /report → 404
- [ ] 他人研究 GET /report → 403

### 代码质量
- [ ] subAgentResults 按 agent_name 排序（与 plan 一致）
- [ ] visitedUrls 为非 NULL 数组
- [ ] 报告 API 响应包含所有必需字段

### 通过判定
全部 ✅ → 任务 Done，进入 Task 22
