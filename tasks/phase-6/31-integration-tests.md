# Task 31: 集成测试

## 对应 Spec
- 全部 specs/auth/06-acceptance.md（AC-AUTH-001 ~ 015）
- 全部 specs/research/06-acceptance.md（AC-RES-001 ~ 024）
- 全部 specs/frontend/06-acceptance.md（AC-FE-001 ~ 016）
- 全部 05-edge-cases.md

## 输入文件（Agent 需读取）
- 全部 `specs/*/06-acceptance.md`
- 全部 `specs/*/05-edge-cases.md`
- `tests/` 下所有已有测试文件
- `docker-compose.yml`（获取服务名和端口）

## 输出文件
- `tests/integration/` 目录:
  - `test_auth_flow.py`（完整注册→登录→me→refresh→ticket 流程）
  - `test_research_full_flow.py`（新建→修改→确认→等待→报告→软删除）
  - `test_sse_flow.py`（SSE 连接 + 事件完整性）
  - `test_rate_limiter.py`（跨端点频控）
  - `test_error_scenarios.py`（边界场景）
- `frontend/e2e/` 目录 (可选):
  - `auth.spec.ts`（Playwright/Cypress E2E）

## 前置任务
- 全部 Phase 2, 3, 4, 5 任务已完成
- 所有 API 接口可用
- 前端可正常启动

## 实现要求

### 1. Auth 集成测试 (`test_auth_flow.py`):
- 完整 Happy Path: 注册 → 获取 token → GET /me → POST /refresh → 新 token 仍有效
- 注册 + 重复注册 → 409
- 注册 + 登录 + 连续 5 次错误密码 → locked
- locked 后正确密码 → 423
- locked 过期 → 自动解锁 + 登录成功
- Ticket: 获取 ticket → 验证有效 → 等待 30s → 验证无效

### 2. Research 全流程测试 (`test_research_full_flow.py`):
- 新建研究 → 验证 plan 含 3-5 sub-agents
- 修改计划 × 2 → planRound 递增
- 第 11 次修改 → 400
- 确认计划 → status='running'
- 等待执行完成 (polling GET /{id})
- 验证 report 非空
- 软删除 → history 不返回
- Token 统计 → 累计值正确

### 3. SSE 流测试 (`test_sse_flow.py`):
- 获取 ticket → 建立 EventSource
- 验证事件序列: sub_agent_start → sub_agent_round → sub_agent_complete → report_complete
- 验证 heartbeat 事件（至少每 30 秒一次）
- 无 ticket → 401
- 过期 ticket → 401
- 他人 research → 403

### 4. 速率限制测试 (`test_rate_limiter.py`):
- Register: 连续 6 次 → 第 6 次 429
- Login: 连续 11 次 → 第 11 次 429
- 不同 IP 的频控独立性
- 窗口重置后恢复

### 5. 边界场景测试 (`test_error_scenarios.py`):
- 参数校验: 空 topic, 无效 template, 超长 feedback
- 权限测试: 访问他人 research → 403
- 状态转换异常: draft 状态下调用 cancel → 400
- 并发保护: 已有 running 研究时新建 → 409
- 数据库异常回滚（模拟 DB 断开）

### 6. (可选) 前端 E2E:
- Playwright 或 Cypress
- 登录 → Dashboard → 新建研究 → 确认计划 → 查看进度 → 查看报告
- SSH Tunneling 或 VNC 用于 Docker 内的浏览器

## 验收检查点（Checkpoint）

### 前置确认
- [ ] 全部 16 个 API 端点可用（curl 逐一验证）
- [ ] 前端所有页面可正常渲染
- [ ] Docker Compose 所有服务 healthy

### 集成验证
- [ ] Auth 集成测试 5 个场景全部 PASS
- [ ] Research 全流程测试 7 个场景全部 PASS
- [ ] SSE 流测试 5 个场景全部 PASS
- [ ] 速率限制测试 4 个场景全部 PASS
- [ ] 边界场景测试 ≥ 6 个场景全部 PASS

### 测试隔离验证
- [ ] 集成测试可独立运行（`pytest tests/integration/` 不依赖特定测试顺序）
- [ ] 每个测试文件有独立的 setup/teardown
- [ ] 数据库数据在每个测试套件前后恢复干净

### 通过判定
全部 ✅ → 任务 Done，进入 Task 32（最终打磨）
