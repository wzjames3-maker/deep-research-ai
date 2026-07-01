# Task 22: 研究历史 + 软删除 + Token 统计

## 对应 Spec
- specs/research/03-api-contract.md:
  - API-RES-007 (GET /history)
  - API-RES-009 (DELETE /{id})
  - API-RES-010 (GET /stats/tokens)
- specs/research/06-acceptance.md AC-RES-015, 016
- specs/research/04-business-rules.md RULE-RES-010, RULE-RES-011

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md（API-RES-007, 009, 010）
- specs/research/06-acceptance.md（AC-RES-015, 016）
- src/repos/research_repo.py（ResearchRepository）
- src/middleware/auth.py
- src/errors.py

## 输出文件
- `src/api/research/router.py`（追加 3 个路由: history, delete, stats）
- `src/api/research/schemas.py`（追加 HistoryResponse, DeleteResponse, TokenStatsResponse）
- `tests/research/test_history.py`（集成测试）

## 前置任务
- Task 14（Research model/repo 可用）
- Task 05（auth middleware 可用）

## 实现要求

### 1. GET `/api/v1/research/history` (API-RES-007):
```
Query: ?page=1&pageSize=20
返回: { items: [...], total: N, page, pageSize }
按 created_at DESC 排序
默认过滤 deleted_at IS NULL
```

```python
class ResearchHistoryItem(BaseModel):
    researchId: UUID
    topic: str
    template: str
    status: str
    totalTokens: int
    createdAt: datetime

class HistoryResponse(BaseModel):
    items: list[ResearchHistoryItem]
    total: int
    page: int
    pageSize: int
```

### 2. DELETE `/api/v1/research/{id}` (API-RES-009) — 软删除:
```
1. Auth
2. 查找 Research (deleted_at IS NULL) → 404
3. 权限检查 → 403
4. 设置 deleted_at = now()
5. 返回 200: { "deleted": true }
```
- 不物理删除子表数据（sub_agent_results, plan_feedbacks）

### 3. GET `/api/v1/research/stats/tokens` (API-RES-010):
```
1. Auth
2. 查询当前用户的 Token 统计:
   - todayTokens: SUM(token_used) WHERE created_at >= today
   - weekTokens: SUM(token_used) WHERE created_at >= week_ago
   - totalResearches: COUNT(*) WHERE deleted_at IS NULL
   - avgTokensPerResearch: totalTokens / totalResearches (completed only)
3. 返回:
   { todayTokens, weekTokens, totalResearches, avgTokensPerResearch }
```

### 4. 测试 (`tests/research/test_history.py`):
- test_list_history: 创建 3 条研究 → 历史返回 3 条, 按时间倒序
- test_list_history_empty: 无研究 → 返回空列表 + total=0
- test_list_history_pagination: 创建 25 条, pageSize=20 → items=20, total=25
- test_soft_delete: DELETE → 200, 历史不再返回该记录
- test_soft_delete_not_found: 不存在 → 404
- test_token_stats: 有 completed 研究 → todayTokens > 0, avgTokensPerResearch 合理

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 14 ResearchRepository 可用
- [ ] 数据库中有测试数据（多条研究记录）

### AC 验收
- [ ] AC-RES-015: DELETE → 200, deleted_at 设置, GET /history 不返回该记录, 数据未物理删除
- [ ] AC-RES-016: GET /stats/tokens → todayTokens, weekTokens, totalResearches, avgTokensPerResearch 均 > 0

### 功能验收
- [ ] GET /history → 按 created_at DESC 排序
- [ ] GET /history?page=2&pageSize=10 → 分页正确
- [ ] 软删除后再次删除同一个 ID → 404（因为 deleted_at IS NOT NULL 过滤）
- [ ] 他人研究不可删除 → 403

### 代码质量
- [ ] Token 统计查询使用 SQL 聚合（不是 Python 循环）
- [ ] 历史查询默认过滤 deleted_at IS NULL
- [ ] 分页参数有默认值，pageSize max=100

### 通过判定
全部 ✅ → 任务 Done。Research 模块完成，进入 Phase 5 (Frontend)
