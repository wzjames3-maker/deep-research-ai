# Task 32: Spec 复查 + 代码打磨

## 对应 Spec
- 全部 specs/（8 层 × 3 模块 = 24 个 spec 文件）
- spec汇总.md

## 输入文件（Agent 需读取）
- 全部 specs/（逐份复查）
- spec汇总.md（交叉引用）
- docs/tech-decision.md（技术选型一致性）

## 输出文件
- 无新文件（仅修改和优化已有代码）
- 逐模块对照复查

## 前置任务
- Task 31（集成测试全部通过）

## 实现要求

### 1. Spec 一致性逐项复查:

#### Auth 模块复查:
- [ ] API 路径/方法/参数与 specs/auth/03-api-contract.md 完全一致
- [ ] 所有 RULE-AUTH-001 ~ 008 在代码中被正确实现
- [ ] 所有 EC-AUTH-001 ~ 009 端点行为被正确处理
- [ ] 所有 AC-AUTH-001 ~ 015 能通过测试

#### Research 模块复查:
- [ ] API 路径/方法/参数与 specs/research/03-api-contract.md 完全一致
- [ ] 所有 RULE-RES-001 ~ 011 在代码中被正确实现
- [ ] 所有 EC-RES-001 ~ 012 端点行为被正确处理
- [ ] 所有 AC-RES-001 ~ 024 能通过测试
- [ ] SSE 8 种事件类型名称与 spec 一致（plan_confirm/sub_agent_start 等）
- [ ] report_markdown ≤ 50000 字符截断逻辑存在

#### Frontend 模块复查:
- [ ] 路由表与 specs/frontend/00-overview.md 一致（6 个路由）
- [ ] `/research/{id}` 状态驱动视图映射正确
- [ ] 所有 RULE-FE-001 ~ 007 在前端代码中被实现
- [ ] 所有 AC-FE-001 ~ 016 能通过测试
- [ ] SSE EventSource 连接使用 ticket 而非 JWT
- [ ] Axios 拦截器正确处理 401 自动登出
- [ ] react-markdown 不渲染 HTML（XSS 防护）

### 2. 代码质量打磨:
- [ ] `.gitignore` 不含 secrets, node_modules, __pycache__, .env
- [ ] 删除所有 `console.log` / `print()` 调试输出
- [ ] 删除所有 `TODO` / `FIXME` 注释（或转为 Issue）
- [ ] 错误处理覆盖所有 `except` 分支（无 bare `except:`）
- [ ] 无硬编码密钥/密码/URL（全部使用 config/env）
- [ ] 无未使用的 import / 变量
- [ ] 所有文件末尾有换行符（EOF newline）
- [ ] Python 代码格式化: `ruff format && ruff check`
- [ ] TypeScript 代码格式化: `prettier --write && tsc --noEmit`
- [ ] Python 类型检查: `mypy src/`

### 3. 文档打磨:
- [ ] `README.md`（如需要）包含:
  - 项目简介
  - 快速开始 (`cp .env.example .env` → `docker compose up -d`)
  - 技术栈说明
  - API 文档链接
- [ ] `.env.example` 包含所有必需变量 + 注释
- [ ] `CHANGELOG.md` 更新（记录 V1 版本的完整变更）

### 4. 性能检查:
- [ ] API 非 LLM 端点 P99 < 200ms
- [ ] SSE 推送延迟 < 1 秒
- [ ] 前端首屏加载 < 3 秒（本地环境）
- [ ] 无 N+1 查询（使用 SQLAlchemy joinedload/selectinload）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 31 集成测试全部 PASS
- [ ] 项目在 Docker Compose 中正常运行

### Spec 复查
- [ ] Auth: 15 AC → 15 PASS, 9 RULE → 9 实现, 9 EC → 9 处理
- [ ] Research: 24 AC → 24 PASS, 11 RULE → 11 实现, 12 EC → 12 处理
- [ ] Frontend: 16 AC → 16 PASS, 7 RULE → 7 实现
- [ ] 接口路径/方法/参数与 spec 100% 一致

### 代码质量
- [ ] `ruff check src/` → 0 error
- [ ] `tsc --noEmit` → 0 error
- [ ] 无 hardcoded secrets（grep `password\|secret\|api_key\|token` 排除 config 读取）
- [ ] 无 debug 输出（grep `console.log\|print(`）

### 部署验证
- [ ] `docker compose up -d` 从零启动成功（`docker compose down -v && docker compose up -d`）
- [ ] 所有 `/api/v1/health` 返回 200
- [ ] 前端可正常访问

### 通过判定
全部 ✅ → 任务 Done。🎉 Phase 6 完成，项目交付
