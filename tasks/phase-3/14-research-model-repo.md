# Task 14: Research 数据模型与 Repository

## 对应 Spec
- specs/research/02-data-model.md（3 张表 + 3 个 ENUM）
- specs/research/04-business-rules.md:
  - RULE-RES-003（修改轮次上限）
  - RULE-RES-004（并发限制）
  - RULE-RES-010（软删除）

## 输入文件（Agent 需读取）
- specs/research/02-data-model.md
- specs/research/04-business-rules.md（RULE-RES-003, 004, 010）
- spec汇总.md §四 数据模型汇总
- src/models/research.py（骨架，Task 02 产出）
- src/models/sub_agent_result.py（骨架）
- src/models/research_plan_feedback.py（骨架）
- src/models/user.py（User 模型引用）

## 输出文件
- `src/models/research.py`（增强 Research 模型）
- `src/models/sub_agent_result.py`（增强 SubAgentResult 模型）
- `src/models/research_plan_feedback.py`（增强 ResearchPlanFeedback 模型）
- `src/repos/research_repo.py`（ResearchRepository）
- `src/repos/sub_agent_result_repo.py`（SubAgentResultRepository）
- `src/repos/plan_feedback_repo.py`（ResearchPlanFeedbackRepository）

## 前置任务
- Task 02（DB Migration，3 张 research 表已创建）
- Task 05（get_db 可用）
- Task 07（User 模型已可用，用于 FK 关系）

## 实现要求

### Research 模型增强方法:
- `has_active_research(user_id: UUID, db) -> bool`: 检查用户是否有 status in ['running', 'draft'] 的研究
- `count_revisions(research_id: UUID, db) -> int`: 当前修改轮次
- `soft_delete()`: 设置 deleted_at = now()
- `has_any_completed_sub_agents(db) -> bool`: 是否有 completed 的 SubAgentResult
- `mark_failed(reason: str)`: status='failed', error_message=reason
- `update_total_tokens(db)`: total_tokens = SUM(sub_agent_results.token_used)
- `to_dict() -> dict`: 返回完整信息，不暴露 deleted_at

### ResearchRepository:
- `create(user_id, topic, template) -> Research`
- `find_by_id(research_id, db) -> Optional[Research]`（过滤 deleted_at IS NULL）
- `find_by_user(user_id, db, page, page_size) -> (List[Research], total)`
- `find_active_by_user(user_id, db) -> Optional[Research]`
- `save(research: Research) -> None`

### SubAgentResultRepository:
- `bulk_create(research_id, sub_agents: List[dict]) -> List[SubAgentResult]`
- `find_by_research(research_id, db) -> List[SubAgentResult]`
- `save(result: SubAgentResult) -> None`

### ResearchPlanFeedbackRepository:
- `create(research_id, round, feedback, plan_snapshot, db) -> ResearchPlanFeedback`
- `count_by_research(research_id, db) -> int`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 02 DB Migration 已创建 researches, sub_agent_results, research_plan_feedbacks 表
- [ ] User 模型可用

### 功能验收
- [ ] `list[Research].create(user_id, topic, template)` → INSERT 成功，status='draft'
- [ ] `find_by_id(id)` → 返回 Research 对象（deleted_at IS NULL）
- [ ] `find_active_by_user(user_id)` → 返回 status in ['draft','running'] 的研究（'confirmed' 为瞬态不持久化，无需查询）
- [ ] `has_active_research()` → 已有 running 的研究时返回 True
- [ ] `soft_delete()` → deleted_at 不为 NULL
- [ ] `bulk_create_sub_agents(research_id, [3个])` → 3 条 SubAgentResult 记录

### 代码质量
- [ ] 所有查询默认过滤 `deleted_at IS NULL`
- [ ] 使用 async SQLAlchemy
- [ ] 无 N+1 查询风险（SubAgentResult 可用 joinedload）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 15
