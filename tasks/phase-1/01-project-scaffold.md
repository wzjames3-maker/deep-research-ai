# Task 01: 项目骨架搭建

## 对应 Spec
- specs/auth/07-tech-constraints.md（FastAPI 项目结构）
- specs/research/07-tech-constraints.md
- docs/tech-decision.md §决策1 (Python + FastAPI)

## 输入文件（Agent 需读取）
- tasks/phase-1/00-container-env.md（了解容器化路径）
- Dockerfile（了解基础镜像和工作目录）
- .env.example（了解环境变量）

## 输出文件
- `src/`
  - `main.py` (FastAPI app factory, CORS, health endpoint)
  - `config.py` (Pydantic Settings, 从 `.env` 加载)
  - `__init__.py`
  - `api/__init__.py`
  - `api/router.py` (主路由聚合)
  - `models/__init__.py`
  - `models/base.py` (SQLAlchemy Base + engine + session)
  - `middleware/__init__.py`
  - `middleware/cors.py` (CORS 配置)
  - `utils/__init__.py`
- `requirements.txt` (完整依赖: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose, bcrypt, httpx, sse-starlette, structlog, litellm, mcp-sdk)
- `alembic.ini` (Alembic 配置，指向 src/models)
- `tests/__init__.py`
- `tests/conftest.py` (pytest fixtures: async test client, test db)

## 前置任务
- Task 00 (容器化环境定义)

## 实现要求
1. **FastAPI App**:
   - `main.py` 创建 `create_app()` 工厂函数
   - 注册 CORS、路由、异常处理器占位
   - `/health` 端点: 检查 DB 连接，返回 `{"status": "ok"}` 或 `{"status": "degraded"}`
2. **Config**:
   - 使用 `pydantic-settings` 的 `BaseSettings`
   - 必需变量: `DATABASE_URL`, `JWT_SECRET` (≥32 字符), `LLM_API_KEY`, `LLM_BASE_URL`, `BRAVE_API_KEY`
- 启动检查: `JWT_SECRET` 为空时拒绝启动，输出 FATAL 日志 (EC-AUTH-006)
   - 可选变量: `JWT_EXPIRES_IN` (default 86400), `BCRYPT_ROUNDS` (default 12)
3. **Database**:
   - SQLAlchemy 2.0 async engine + async session factory
   - `models/base.py` 导出 `Base` 和 `get_db` async generator
4. **Router 聚合**:
   - `api/router.py` 作为 `APIRouter(prefix="/api/v1")`
   - 预留 `auth.router` 和 `research.router` 子路由挂载点
5. **测试基础设施**:
   - `conftest.py`: 使用 `httpx.ASGITransport` 的 async test client
   - 测试数据库使用独立 schema 或 DATABASE_URL 覆盖

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 00 容器环境已可正常启动 (`docker compose up -d`)
- [ ] Dockerfile 基础镜像和工作目录路径已知

### 功能验收
- [ ] `docker compose up -d` 后 `curl http://localhost:8000/health` → `{"status": "ok"}`
- [ ] `docker compose exec app python -c "from src.config import settings; print(settings.DATABASE_URL)"` 正常
- [ ] `alembic upgrade head` 不报错（虽然 schema 为空）
- [ ] `pytest tests/` 至少 1 个测试通过（最简单的 health endpoint 测试）

### 代码质量
- [ ] `requirements.txt` 中所有包版本已固定（非 `>=`）
- [ ] `main.py` 无明显逻辑错误
- [ ] `config.py` 中无硬编码密钥/密码
- [ ] `.env.example` 与 config 变量一一对应

### Spec 一致性
- [ ] FastAPI 项目结构与 tech-decision.md 一致
- [ ] API 前缀 `/api/v1` 与所有 spec 的 03-api-contract.md 一致
- [ ] 异步 SQLAlchemy 实现与 tech-decision.md §决策1 一致

### 通过判定
全部 ✅ → 任务 Done，进入 Task 02
