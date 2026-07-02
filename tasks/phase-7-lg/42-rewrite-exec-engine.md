# Task 42: 重写 exec_engine.py → Graph 调用包装器

## 对应 Spec
- specs/research/08-dependencies.md §API 层调用接口
- specs/research/04-business-rules.md RULE-RES-009（Hybrid 取消）

## 输入文件（Agent 需读取）
- specs/research/08-dependencies.md §API 层调用接口
- specs/research/04-business-rules.md RULE-RES-009
- src/services/research_graph.py（Task 41: get_research_graph）
- src/services/exec_engine.py（当前实现 — 需重写）
- src/services/sse_manager.py

## 输出文件
- `src/services/exec_engine.py`（重写为 thin graph wrapper）

## 前置任务
- Task 41（main graph 已编译）

## 实现要求

### 保留的接口（外部调用方不改动）

```python
# 这两个函数签名不变，内部实现改为 graph 调用

async def cancel_execution(research_id: uuid.UUID) -> None:
    """Signal the execution engine to cancel."""
    # 1. asyncio.Event 实时信号（Sub-agent 每轮检查）
    if research_id not in cancel_signals:
        cancel_signals[research_id] = asyncio.Event()
    cancel_signals[research_id].set()

    # 2. graph update_state 持久化（崩溃恢复用）
    graph = get_research_graph()
    config = {"configurable": {"thread_id": str(research_id)}}
    try:
        await graph.aupdate_state(config, {"cancel_requested": True})
    except Exception:
        pass  # graph 可能未在运行，忽略


async def check_cancelled(research_id: uuid.UUID) -> bool:
    """Check if execution has been cancelled."""
    return cancel_signals.get(research_id, asyncio.Event()).is_set()


# 保留 cancel_signals dict（Sub-agent subgraph 内部使用）
cancel_signals: dict[uuid.UUID, asyncio.Event] = {}
```

### 新增接口

```python
async def run_research(db_session_factory, research_id: uuid.UUID) -> None:
    """Background task: resume graph with confirm action.

    Called by confirm_plan via asyncio.create_task().
    Uses Command(resume={"action":"confirm"}) to resume from interrupt().
    """
    cancel_signals[research_id] = asyncio.Event()

    graph = get_research_graph()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }

    try:
        # Command(resume=...) 从 human_review interrupt 恢复，执行 confirm 路径
        from langgraph.types import Command
        await graph.ainvoke(Command(resume={"action": "confirm"}), config)
    except Exception as e:
        logger.error("exec_engine_error", research_id=str(research_id), error=str(e))
        # 更新 DB status='failed'
        ...
    finally:
        cancel_signals.pop(research_id, None)


async def start_research_graph(
    db_session_factory, topic: str, template: str, user_id: uuid.UUID
) -> dict:
    """Start new research graph (called by POST /new).

    Runs graph until interrupt() → returns plan.
    Pre-generates research_id so plan_generation_node can use it for DB record.
    """
    graph = get_research_graph()
    research_id = uuid.uuid4()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }

    result = await graph.ainvoke(
        {"topic": topic, "template": template, "user_id": user_id, "research_id": research_id},
        config,
    )
    # 返回 plan + research_id（graph 在 human_review interrupt 暂停）
    return {"research_id": research_id, "plan": result["plan"], "plan_round": result["plan_round"]}


async def resume_research_graph(
    db_session_factory, research_id: uuid.UUID, action: str, feedback: str | None = None
) -> dict:
    """Resume graph with user action (called by POST /revise only).

    action='revise' → plan_revision → 回到 interrupt → 返回新 plan
    action='confirm' is NOT used here — confirm uses run_research() as background task instead.
    """
    graph = get_research_graph()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }

    resume_value = {"action": action}
    if feedback:
        resume_value["feedback"] = feedback

    from langgraph.types import Command
    result = await graph.ainvoke(Command(resume=resume_value), config)

    # graph 回到 interrupt → 返回新 plan
    return {"plan": result["plan"], "plan_round": result["plan_round"]}


async def recover_research(db_session_factory, research_id: uuid.UUID) -> None:
    """Recover a crashed research from checkpoint.

    Called on app startup for status='running' researches.
    Uses ainvoke(None) to continue from last checkpoint (NOT interrupt resume).
    If the graph was at an interrupt, ainvoke(None) returns current state without advancing.
    """
    graph = get_research_graph()
    config = {
        "configurable": {
            "thread_id": str(research_id),
            "db_session_factory": db_session_factory,
        }
    }
    # ainvoke(None) = 从 checkpoint 恢复（崩溃恢复专用，不用于 interrupt resume）
    await graph.ainvoke(None, config)
```

### 删除的函数

- `_run_sub_agent` → 被 sub_agent_graph 替代
- `_aggregate_results` → 被 aggregate_node 替代
- `_handle_cancel_aggregation` → 被 partial_aggregate_node 替代
- `_format_search_results` → 移到 sub_agent_graph.py
- `ResearchState` TypedDict → 使用 graph_state.py 中的定义

### 保留的模块级变量

- `cancel_signals: dict[uuid.UUID, asyncio.Event]` — asyncio.Event 实时取消信号
- `cancel_execution()` / `check_cancelled()` — 接口不变，内部增加 update_state 调用

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 41 main graph 已编译

### 功能验证
- [ ] `start_research_graph()` 运行到 interrupt → 返回 plan（pre-generates research_id）
- [ ] `resume_research_graph(action='revise')` → plan_revision → 回到 interrupt → 返回新 plan
- [ ] `run_research()` 使用 `Command(resume={"action":"confirm"})` 从 interrupt 恢复（后台执行）
- [ ] `recover_research()` 使用 `ainvoke(None)` 从 checkpoint 恢复（崩溃恢复专用）
- [ ] `cancel_execution()` 同时设置 asyncio.Event + update_state
- [ ] `check_cancelled()` 接口不变
- [ ] `_run_sub_agent`, `_aggregate_results` 等旧函数已删除

### 代码质量
- [ ] exec_engine.py 行数 < 100（thin wrapper）
- [ ] 无业务逻辑（全部委托 graph）
- [ ] logger 错误处理保留
- [ ] cancel_signals 清理在 finally 中

### 通过判定
全部 ✅ → 任务 Done，进入 Task 43
