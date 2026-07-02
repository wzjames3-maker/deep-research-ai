# Task 39: Plan 节点实现

## 对应 Spec
- specs/research/04-business-rules.md RULE-RES-002, RULE-RES-003
- specs/research/07-tech-constraints.md §interrupt() Human-in-the-loop

## 输入文件（Agent 需读取）
- specs/research/04-business-rules.md RULE-RES-002, 003
- specs/research/07-tech-constraints.md §interrupt(), §RunnableConfig 注入
- src/services/llm_service.py（generate_plan, revise_plan）
- src/repos/research_repo.py（ResearchRepository）
- src/repos/sub_agent_result_repo.py（SubAgentResultRepository）
- src/repos/plan_feedback_repo.py（ResearchPlanFeedbackRepository）
- src/services/sse_manager.py
- src/services/graph_state.py（Task 34: ResearchState）
- src/errors.py（ResearchInProgressError, PlanGenerationFailedError, TooManyRevisionsError）

## 输出文件
- `src/services/research_graph.py`（部分实现: plan_generation_node, human_review_node, plan_revision_node）

## 前置任务
- Task 34（ResearchState 定义可用）
- Task 15（llm_service 可用）

## 实现要求

### plan_generation_node

```python
async def plan_generation_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Generate research plan using LLM."""
    db_factory = config["configurable"]["db_session_factory"]
    topic = state["topic"]
    template = state["template"]

    # RULE-RES-001: 检查并发
    # RULE-RES-002: LLM 生成 plan (3-5 sub-agents)
    plan, plan_tokens = await llm_service.generate_plan(topic, template)

    # 创建 Research 记录 (status='draft')
    # 创建 SubAgentResult 记录 (status='pending')
    # 返回更新后的 state
    return {
        "plan": plan,
        "plan_round": 1,
        "total_tokens": plan_tokens,
        "status": "draft",
        "research_id": research.id,
    }
```

### human_review_node

```python
from langgraph.types import interrupt

async def human_review_node(state: ResearchState) -> dict:
    """Pause graph execution, wait for user action."""
    # interrupt() 暂停 graph
    # API 层通过 Command(resume={...}) 恢复
    user_action = interrupt({
        "plan": state["plan"],
        "plan_round": state["plan_round"],
        "status": "awaiting_review",
    })
    # user_action 来自 resume value: {"action": "confirm"} 或 {"action": "revise", "feedback": "..."}
    return {"feedback": user_action.get("feedback"), "_action": user_action["action"]}
```

### plan_revision_node

```python
async def plan_revision_node(state: ResearchState, config: RunnableConfig) -> dict:
    """Revise plan based on user feedback."""
    db_factory = config["configurable"]["db_session_factory"]
    feedback = state["feedback"]

    # RULE-RES-003: 检查修改轮次 (max 10)
    # 调用 llm_service.revise_plan(topic, current_plan, feedback)
    new_plan, revise_tokens = await llm_service.revise_plan(
        state["topic"], state["plan"], feedback
    )

    # 删除旧 SubAgentResult, 创建新记录
    # 保存 ResearchPlanFeedback 快照
    # 返回更新后的 state
    return {
        "plan": new_plan,
        "plan_round": state["plan_round"] + 1,
        "total_tokens": state["total_tokens"] + revise_tokens,
    }
```

### Conditional Edge: route_after_review

```python
def route_after_review(state: ResearchState) -> str:
    """Route to revision or dispatch based on user action."""
    action = state.get("_action", "confirm")
    if action == "revise":
        return "plan_revision"
    return "dispatch"
```

### SSE 事件
- `plan_generation_node`: 无 SSE 推送（API 同步返回 plan）
- `human_review_node`: 无 SSE 推送（graph 暂停等待用户）
- `plan_revision_node`: 无 SSE 推送（API 同步返回新 plan）

### DB 操作
- `plan_generation_node`: 创建 Research + SubAgentResult（bulk）
- `plan_revision_node`: 更新 plan_json, 删除旧 SubAgentResult + 创建新, 保存 ResearchPlanFeedback
- 每个节点内通过 config 获取 db_session_factory，创建独立 session

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 34 ResearchState 可 import
- [ ] Task 15 llm_service.generate_plan/revise_plan 可用

### 功能验证
- [ ] plan_generation_node: LLM 调用 → 3-5 sub-agents → DB 创建 Research + SubAgentResult
- [ ] human_review_node: interrupt() 正确暂停 graph
- [ ] plan_revision_node: LLM 调用 → 更新 plan → 删除旧 SubAgentResult → 创建新
- [ ] route_after_review: action='revise' → 'plan_revision'; action='confirm' → 'dispatch'
- [ ] plan_revision 后 graph 回到 human_review interrupt

### 代码质量
- [ ] DB session 通过 config 注入
- [ ] 无裸 try/except
- [ ] RULE-RES-003 修改轮次检查存在
- [ ] research_id 在 plan_generation 后写入 state

### 通过判定
全部 ✅ → 任务 Done，进入 Task 40
