# Task 34: State Schema 定义

## 对应 Spec
- specs/research/07-tech-constraints.md（State 定义 + State Reducer）
- specs/research/08-dependencies.md（Graph Node 函数签名）

## 输入文件（Agent 需读取）
- specs/research/07-tech-constraints.md
- specs/research/08-dependencies.md
- src/models/research.py（ORM 模型字段参考）
- src/models/sub_agent_result.py

## 输出文件
- `src/services/graph_state.py`（NEW: ResearchState + SubAgentState TypedDict）

## 前置任务
- Task 33（langgraph 已安装）

## 实现要求

### 1. ResearchState（主 Graph State）
```python
from typing import Annotated, TypedDict
from uuid import UUID
import operator

class ResearchState(TypedDict):
    research_id: UUID
    user_id: UUID
    topic: str
    template: str
    plan: list[dict]
    plan_round: int
    feedback: str | None
    _action: str | None           # interrupt resume 值: "confirm" | "revise"
    sub_agent_results: Annotated[list[dict], operator.add]  # reducer: Send API 并行结果累加
    cancel_requested: bool
    report_markdown: str
    total_tokens: int
    status: str
    error_message: str | None
```

> **注意**: `research_id` 由 `start_research_graph()` 在 API 层 pre-generate（`uuid.uuid4()`），
> 通过 `graph.ainvoke({"research_id": research_id, ...})` 传入。
> `plan_generation_node` 创建 DB 记录时必须使用此 `research_id`（`repo.create(id=research_id, ...)`），
> 而非依赖 DB 的 `DEFAULT gen_random_uuid()`。

### 2. SubAgentState（Sub-agent Subgraph State）
```python
class SubAgentState(TypedDict):
    research_id: UUID
    topic: str
    agent_def: dict            # {name, goal, searchDirection}
    search_direction: str
    visited_urls: list[str]
    findings: str
    rounds_completed: int
    sufficient: bool
    token_used: int
    status: str
    has_error: bool               # 是否遇到错误（影响 complete_node 状态判定）
```

### 3. 约束
- 必须使用 `TypedDict`（非 Pydantic BaseModel），因 LangGraph 要求 TypedDict + Annotated reducer
- `sub_agent_results` 的 `Annotated[list[dict], operator.add]` 是关键：确保 Send API fan-out 后多个 Sub-agent 结果累加而非覆盖
- `_action` 字段由 `human_review_node` 从 `interrupt()` resume 值中提取，用于 `route_after_review` conditional edge 路由
- 不包含任何不可序列化的对象（DB session、asyncio.Event 等）

### 4. research_id 约定
- `research_id` 由 `start_research_graph()` 在 API 层 pre-generate（`uuid.uuid4()`）
- 传入 graph 的初始 state：`{"research_id": research_id, ...}`
- `plan_generation_node` 创建 DB 记录时**必须使用此 research_id**（`repo.create(id=research_id, ...)`），不能用 DB 的 `DEFAULT gen_random_uuid()`
- thread_id = `str(research_id)`，确保 checkpoint 和 DB 记录一一对应

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 33 langgraph 已安装
- [ ] `import langgraph` 成功

### AC 验收
- [ ] `graph_state.py` 可导入
- [ ] `ResearchState` 和 `SubAgentState` 类型定义正确
- [ ] `sub_agent_results` 使用 `Annotated[list[dict], operator.add]` reducer

### 通过判定
全部 ✅ → 任务 Done，进入 Task 35
