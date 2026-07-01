# Task 00: 容器化环境定义

## 对应 Spec
- specs/auth/07-tech-constraints.md
- specs/research/07-tech-constraints.md
- docs/tech-decision.md §决策8 (Docker Compose)

## 输入文件（Agent 需读取）
- docs/tech-decision.md（完整技术选型）
- docs/research-report.md §模块2 (Brave Search MCP)

## 输出文件
- `docker-compose.yml`（锁定所有版本号）
- `Dockerfile`（Python 3.12 镜像）
- `Dockerfile.nginx`（Nginx 反向代理）
- `.env.example`

## 前置任务
- 无（最优先任务）

## 实现要求
1. **Python 服务 (Dockerfile)**:
   - 基础: `python:3.12-slim`
   - 依赖管理: `requirements.txt` 通过 pip 安装
   - 工作目录: `/app`
   - CMD: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
2. **PostgreSQL**:
   - 镜像: `postgres:16-alpine`
   - 默认数据库名: `deepresearch`
   - 环境变量通过 `.env` 注入
3. **Brave Search MCP**:
   - 使用 [brave-search-mcp](https://github.com/langchain-ai/brave-search-mcp) Docker 镜像
   - 作为独立 service 运行，FastAPI 通过 HTTP 或 MCP 协议通信
4. **Nginx**:
   - 反向代理前端 (port 5173 dev) 或 built static files (port 80)
   - 代理 `/api/*` 到 FastAPI 8000
   - Access log 配置（注意不记录 `?ticket=` 参数用于安全）
5. **版本锁定**:
   - 所有镜像使用精确版本号（非 `latest`）
   - Python 包版本在 `requirements.txt` 中固定

## 验收检查点（Checkpoint）

### 前置确认
- [ ] 无前置依赖

### 环境验证
- [ ] `docker compose up -d` 全部服务启动成功
- [ ] `docker compose ps` 全部 service status = "Up" 或 "healthy"
- [ ] FastAPI 容器 `curl http://localhost:8000/health` 返回 200（待 scaffold 实现）
- [ ] PostgreSQL 容器可连接 (`docker compose exec db psql -U user -d deepresearch -c "SELECT 1"`)
- [ ] Nginx 容器 `curl http://localhost/` 不返回错误

### 文件质量
- [ ] `.env.example` 包含所有必需环境变量（含注释说明）
- [ ] 无不安全的默认值（如弱密码）—— 使用占位符 `CHANGE_ME`
- [ ] `docker-compose.yml` 不含硬编码密钥

### 通过判定
全部 ✅ → 任务 Done，进入 Task 01
