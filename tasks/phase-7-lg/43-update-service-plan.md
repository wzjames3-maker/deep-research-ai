# Task 43: 更新 service_plan.py (invoke/resume)

## 对应 Spec
- specs/research/03-api-contract.md API-RES-001, 002, 003（V1.1.0 实现变更注释）
- specs/research/08-dependencies.md §API 层调用接口

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md API-RES-001, 002, 003
- specs/research/08-dependencies.md §API 层调用接口
- src/api/research/service_plan.py（当前实现）
- src/services/exec_engine.py（Task 42: start_research_graph, resume_research_graph, run_research）
- src/repos/research_repo.py

## 输出文件
- `src/api/research/service_plan.py`（更新 create/revise/confirm）

## 前置任务
- Task 42（exec_engine graph wrapper 可用）

## 实现要求

### create_research（API-RES-001）

```python
async def create_research(db: AsyncSession, user: User, topic: str, template: str) -> dict:
    """POST /new — Start new research graph."""
    # RULE-RES-001: 检查并发（保留现有逻辑）
    repo = ResearchRepository(db)
    if await repo.has_running_by_user(user.id):
        raise ResearchInProgressError("当前有一个进行中的研究")

    # 创建 db_session_factory（与 confirm 逻辑一致）
    engine = db.bind
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 启动 graph → 运行到 interrupt → 返回 plan + research_id
    from src.services.exec_engine import start_research_graph
    result = await start_research_graph(session_factory, topic, template, user.id)

    # 返回格式不变
    return {
        "researchId": str(result["research_id"]),
        "plan": _build_plan_response(result["plan"]),
        "planRound": result["plan_round"],
    }
```

### revise_plan（API-RES-002）

```python
async def revise_plan(db: AsyncSession, user: User, research_id, feedback: str) -> dict:
    """POST /revise — Resume graph with revise action."""
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权操作该研究")
    if research.status != "draft":
        raise InvalidStatusError("当前状态不允许修改计划")

    # RULE-RES-003: 检查修改轮次
    fb_repo = ResearchPlanFeedbackRepository(db)
    revision_count = await fb_repo.count_by_research(research.id)
    if revision_count >= MAX_REVISIONS:
        raise TooManyRevisionsError(...)

    # Resume graph with revise action
    engine = db.bind
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from src.services.exec_engine import resume_research_graph
    result = await resume_research_graph(session_factory, research_id, "revise", feedback)

    # 返回格式不变
    return {
        "plan": _build_plan_response(result["plan"]),
        "planRound": result["plan_round"],
    }
```

### confirm_plan（API-RES-003）

```python
async def confirm_plan(db: AsyncSession, user: User, research_id) -> dict:
    """POST /confirm — Trigger background graph execution with confirm action."""
    repo = ResearchRepository(db)
    research = await repo.find_by_id(research_id)

    if research is None:
        raise NotFoundError("研究记录不存在")
    if research.user_id != user.id:
        raise ForbiddenError("无权操作该研究")
    if research.status != "draft":
        raise InvalidStatusError("当前状态不允许确认计划")

    # 更新 status → running（兼容现有 DB 逻辑）
    research.status = "running"
    research.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(research)

    # 后台执行 graph: run_research 内部调用 Command(resume={"action":"confirm"})
    engine = db.bind
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from src.services.exec_engine import run_research
    asyncio.create_task(run_research(session_factory, research_id))

    return {
        "researchId": str(research.id),
        "status": research.status,
        "streamUrl": f"/api/v1/research/{research.id}/stream",
    }
```

### 不改动的函数
- `get_research_detail` — 纯 DB 查询，无 graph 依赖
- `get_research_report` — 纯 DB 查询
- `get_history` — 纯 DB 查询
- `soft_delete_research` — 需追加 checkpoint 清理（见 Task 44）
- `get_token_stats` — 纯 DB 查询
- `_build_plan_response` / `_build_sub_agent_results` — 辅助函数不变

### 兼容性说明
- **API 请求/响应格式完全不变**（前端无感知）
- research_id 由 graph 在 plan_generation_node 中创建（通过 start_research_graph 返回）
- plan_json 仍由 plan_generation_node 写入 DB
- SubAgentResult 仍由 plan_generation_node / plan_revision_node 创建

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 42 exec_engine graph wrapper 可用
- [ ] start_research_graph, resume_research_graph 可调用

### 功能验证
- [ ] POST /new → 返回 {researchId, plan, planRound}（格式不变）
- [ ] POST /revise → 返回 {plan, planRound}（格式不变）
- [ ] POST /confirm → 返回 {researchId, status, streamUrl}（格式不变）
- [ ] RULE-RES-001 并发检查保留
- [ ] RULE-RES-003 修改轮次检查保留
- [ ] confirm 后 asyncio.create_task(run_research()) 后台执行

### 代码质量
- [ ] API 响应格式与 03-api-contract.md 完全一致
- [ ] 错误码不变（404, 403, 400, 409, 500）
- [ ] db_session_factory 创建方式一致

### 通过判定
全部 ✅ → 任务 Done，进入 Task 44
