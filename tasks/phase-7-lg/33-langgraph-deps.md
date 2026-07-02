# Task 33: LangGraph 依赖安装 + PostgresSaver 初始化

## 对应 Spec
- specs/research/07-tech-constraints.md（LangGraph 架构约束 + 实现级选型表）
- specs/research/08-dependencies.md（前置依赖：langgraph + langgraph-checkpoint-postgres）
- docs/tech-decision.md §决策4（LangGraph 全流程编排）

## 输入文件（Agent 需读取）
- specs/research/07-tech-constraints.md
- specs/research/08-dependencies.md
- src/config.py（DATABASE_URL 等环境变量）
- requirements.txt（现有依赖列表）
- docker-compose.yml（PostgreSQL 连接信息）

## 输出文件
- `requirements.txt`（追加 langgraph, langgraph-checkpoint-postgres）
- `src/services/checkpointer.py`（NEW: PostgresSaver 初始化 + setup()）
- `src/main.py`（lifespan 中调用 checkpointer.setup()）
- `Dockerfile`（如需重建镜像）

## 前置任务
- 无（Phase 7-LG 起始任务）

## 实现要求

### 1. 添加依赖
```
# requirements.txt 追加
langgraph>=0.2.0
langgraph-checkpoint-postgres>=2.0.0
```

### 2. PostgresSaver 初始化（src/services/checkpointer.py）

> **注意**: app 全异步，使用 `AsyncPostgresSaver`（非同步 `PostgresSaver`）。
> 如果 `AsyncPostgresSaver` 在当前版本不可用，降级为同步 `PostgresSaver` + `run_in_executor` 包装。

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.config import settings

_checkpointer: AsyncPostgresSaver | None = None

async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
        await _checkpointer.setup()  # 创建 checkpoint 表
    return _checkpointer
```

### 3. 应用启动时初始化
- `src/main.py` 的 `lifespan` 中调用 `await get_checkpointer()`
- 确保 checkpoint 表在应用启动时已创建

### 4. 验证
- `docker compose exec app python -c "from src.services.checkpointer import get_checkpointer; import asyncio; asyncio.run(get_checkpointer())"` 成功
- PostgreSQL 中出现 `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` 三张表

## 验收检查点（Checkpoint）

### 前置确认
- [ ] PostgreSQL 16 可用
- [ ] Docker Compose 可重建 app 镜像

### AC 验收
- [ ] `langgraph` 和 `langgraph-checkpoint-postgres` 在 requirements.txt 中
- [ ] `docker compose build app` 成功（依赖可安装）
- [ ] `docker compose exec app python -c "import langgraph; print(langgraph.__version__)"` 成功
- [ ] `checkpointer.py` 可导入且 `get_checkpointer()` 可执行
- [ ] PostgreSQL 中出现 3 张 checkpoint 表

### 通过判定
全部 ✅ → 任务 Done，进入 Task 34
