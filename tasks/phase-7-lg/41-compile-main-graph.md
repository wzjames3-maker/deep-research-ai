# Task 41: 编译 Main Graph + PostgresSaver

## 对应 Spec
- specs/research/07-tech-constraints.md §StateGraph 结构, §PostgresSaver Checkpointer, §State 定义

## 输入文件（Agent 需读取）
- specs/research/07-tech-constraints.md §LangGraph 架构约束（完整结构图）
- src/services/research_graph.py（Task 39+40 产出: 所有 node 函数）
- src/services/sub_agent_graph.py（Task 38: compile_sub_agent_graph）
- src/services/graph_state.py（Task 34: ResearchState, SubAgentState）
- src/services/checkpointer.py（Task 33: get_checkpointer）

## 输出文件
- `src/services/research_graph.py`（追加: compile_research_graph 函数）

## 前置任务
- Task 33（PostgresSaver 初始化可用）
- Task 38（sub_agent_graph 已编译）
- Task 39（plan 节点已实现）
- Task 40（dispatch + aggregate 节点已实现）

## 实现要求

### compile_research_graph 函数

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

def compile_research_graph(checkpointer=None) -> CompiledGraph:
    """Assemble all nodes and edges into the main research graph.

    Args:
        checkpointer: PostgresSaver for production, MemorySaver for testing.
                      If None, uses get_checkpointer().
    """
    if checkpointer is None:
        checkpointer = get_checkpointer()

    builder = StateGraph(ResearchState)

    # ── Nodes ──
    builder.add_node("plan_generation", plan_generation_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("plan_revision", plan_revision_node)
    builder.add_node("dispatch", dispatch_node)

    # Sub-agent subgraph as a node
    compiled_sub_agent = compile_sub_agent_graph()
    builder.add_node("sub_agent_graph", compiled_sub_agent)

    builder.add_node("aggregate", aggregate_node)
    builder.add_node("partial_aggregate", partial_aggregate_node)

    # ── Edges ──
    builder.set_entry_point("plan_generation")
    builder.add_edge("plan_generation", "human_review")

    # human_review → (conditional) → plan_revision or dispatch
    builder.add_conditional_edges("human_review", route_after_review, {
        "plan_revision": "plan_revision",
        "dispatch": "dispatch",
    })

    # plan_revision → back to human_review
    builder.add_edge("plan_revision", "human_review")

    # dispatch → sub_agent_graph (via Send API, automatic fan-out)
    builder.add_edge("dispatch", "sub_agent_graph")

    # sub_agent_graph → check_cancel (conditional)
    builder.add_conditional_edges("sub_agent_graph", check_cancel, {
        "aggregate": "aggregate",
        "partial_aggregate": "partial_aggregate",
    })

    # aggregate / partial_aggregate → END
    builder.add_edge("aggregate", END)
    builder.add_edge("partial_aggregate", END)

    return builder.compile(checkpointer=checkpointer)
```

### Graph 单例

```python
# 模块级单例（延迟初始化）
_compiled_graph = None

def get_research_graph() -> CompiledGraph:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_research_graph()
    return _compiled_graph
```

### PostgresSaver 集成

- `checkpointer.py` 的 `get_checkpointer()` 返回 `AsyncPostgresSaver` 实例
- `compile_research_graph()` 默认使用 `get_checkpointer()`
- 测试时可传入 `MemorySaver` 替代

### thread_id 约定

- `thread_id = str(research_id)`
- 所有 `graph.ainvoke()` / `graph.aupdate_state()` 调用都使用此 config:
  ```python
  config = {"configurable": {"thread_id": str(research_id), "db_session_factory": factory}}
  ```

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 33 PostgresSaver setup() 已执行
- [ ] Task 38 compile_sub_agent_graph 可调用
- [ ] Task 39 所有 plan 节点函数已定义
- [ ] Task 40 dispatch + aggregate 节点函数已定义

### 功能验证
- [ ] `compile_research_graph()` 不抛异常
- [ ] 返回的 CompiledGraph 有 `.ainvoke()`, `.aupdate_state()` 方法
- [ ] 使用 MemorySaver 也能编译（测试用）
- [ ] `get_research_graph()` 返回单例
- [ ] Graph 结构与 07-tech-constraints.md 结构图一致

### 代码质量
- [ ] 所有节点已注册
- [ ] 所有边已连接
- [ ] conditional edges 的路由映射完整
- [ ] checkbreaker 正确传入

### 通过判定
全部 ✅ → 任务 Done，进入 Task 42
