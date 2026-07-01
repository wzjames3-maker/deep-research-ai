# 任务总览

## 里程碑映射

| 里程碑 | 内容 | 对应 Phase |
|---|---|---|
| M1 | 基础设施 + Auth | Phase 1 + Phase 2 |
| M2 | 研究计划生成 + Sub-agent 单路执行 + 报告 | Phase 3 + Phase 4 (task 14-21) |
| M3 | 并行执行 + SSE 实时推送 | Phase 4 (task 19) |
| M4 | 前端工作台 UI（计划/进度/报告） | Phase 5 (task 23-29) |
| M5 | 历史 + Token 仪表盘 + 复制导出 | Phase 5 (task 25, 30) |
| M6 | 联调与上线 | Phase 6 |

---

## 进度看板

| # | Phase | 任务 | 状态 | 对应 Spec | 对应 AC |
|---|---|---|---|---|---|
| 00 | 1 | 容器化环境定义 | ✅ Done | tech-decision §决策8 | — |
| 01 | 1 | 项目骨架搭建 | ✅ Done | tech-decision §决策1 | — |
| 02 | 1 | 数据库 Migration | ✅ Done | auth/02 + research/02 | — |
| 03 | 1 | 统一错误码体系 | ✅ Done | auth/03 + research/03 错误码 | — |
| 04 | 1 | 速率限制中间件 | ✅ Done | auth/03 429 错误码 | AC-AUTH-012 |
| 05 | 1 | 认证中间件 (JWT Depends) | ✅ Done | auth/03 API-AUTH-003 | AC-AUTH-010 |
| 06 | 1 | 结构化日志配置 | ✅ Done | tech-decision | — |
| 07 | 2 | Auth 数据模型与 Repository | ✅ Done | auth/02 + auth/04 RULE-003/005 | — |
| 08 | 2 | Auth 工具函数 (bcrypt + JWT + TicketStore) | ✅ Done | auth/04 RULE-001~002/004/007/008 | AC-001/004/005/015 |
| 09 | 2 | 注册接口 — 测试 (TDD: RED) | ✅ Done | auth/03 API-AUTH-001 | AC-AUTH-001, 002, 003, 011 |
| 10 | 2 | 注册接口 — 实现 (TDD: GREEN) | ✅ Done | auth/03 API-AUTH-001 | AC-AUTH-001, 002, 003, 011 |
| 11 | 2 | 登录接口 — 测试 (TDD: RED) | ✅ Done | auth/03 API-AUTH-002 | AC-AUTH-004~009, 012 |
| 12 | 2 | 登录接口 — 实现 (TDD: GREEN) | ✅ Done | auth/03 API-AUTH-002 | AC-AUTH-004~009, 012 |
| 13 | 2 | /me + /refresh + /ticket 接口 | ✅ Done | auth/03 API-AUTH-004~006 | AC-AUTH-013, 014, 015 |
| 14 | 3 | Research 数据模型与 Repository | ✅ Done | research/02 + research/04 RULE-003~004, RULE-010 | — |
| 15 | 3 | LLM 服务封装 (LiteLLM + Prompt 模板) | ✅ Done | research/04 RULE-002~003, 005, 008 | — |
| 16 | 3 | MCP 搜索客户端 (Brave Search) | ✅ Done | research/08 + research/04 RULE-005~006 | AC-RES-008 |
| 17 | 4 | 研究计划 — 测试 (TDD: RED) | ✅ Done | research/03 API-RES-001~003, API-RES-005 | AC-RES-001~006, 019, 022, 023 |
| 18 | 4 | 研究计划 — 实现 (TDD: GREEN) | ✅ Done | research/03 API-RES-001~003, API-RES-005 | AC-RES-001~006, 019, 022, 023 |
| 19 | 4 | 研究执行引擎 + SSE 流 | ✅ Done | research/03 API-RES-004 + research/04 RULE-004~009, 011 | AC-RES-007~011, 021, 024 |
| 20 | 4 | 研究中断接口 | ✅ Done | research/03 API-RES-008 + research/04 RULE-009 | AC-RES-012, 013 |
| 21 | 4 | 研究报告接口 | ✅ Done | research/03 API-RES-006 + research/04 RULE-007, RULE-010 | AC-RES-014, 016, 020 |
| 22 | 4 | 研究历史 + 软删除 + Token 统计 | ✅ Done | research/03 API-RES-007, 009, 010 | AC-RES-015, 016 |
| 23 | 5 | 前端项目骨架 (Vite + Router + 拦截器 + 设计系统) | ✅ Done | frontend/00 + tech-decision §决策3~5 | AC-FE-015 |
| 24 | 5 | 登录/注册页面 | ✅ Done | frontend/01 REQ-FE-001 | AC-FE-001, 002, 016 |
| 25 | 5 | 仪表盘页面 | ✅ Done | frontend/01 REQ-FE-010 | AC-FE-013 |
| 26 | 5 | 新建研究页面 | ✅ Done | frontend/01 REQ-FE-002 | AC-FE-003 |
| 27 | 5 | PlanPanel 视图 (计划审核+修改) | ✅ Done | frontend/01 REQ-FE-003 | AC-FE-004, 005 |
| 28 | 5 | ProgressDashboard 视图 (SSE 消费) | ✅ Done | frontend/01 REQ-FE-004 + REQ-FE-011 | AC-FE-006, 007, 014 |
| 29 | 5 | ReportView 视图 (Tab + 复制) | ✅ Done | frontend/01 REQ-FE-005~007 + research/06 AC-RES-017~018 | AC-FE-008, 009, 010 + AC-RES-017, 018 |
| 30 | 5 | 研究历史页面 | ✅ Done | frontend/01 REQ-FE-008 + REQ-FE-009 | AC-FE-011, 012 |
| 31 | 6 | 集成测试 | ✅ Done | 全部 AC | 全部 AC |
| 32 | 6 | Spec 复查 + 代码打磨 | ✅ Done | 全部 spec | — |

---

## 任务状态图例

| 状态 | 含义 |
|---|---|
| ⬜ Todo | 等待执行 |
| 🟡 In Progress | 正在执行（Agent 工作中） |
| 🔴 RED | TDD 测试任务完成（测试全红，等待实现） |
| ✅ Done | 任务完成并通过检查点 |
| 🔴 BLOCKED | 修复次数 ≥ 3，暂停待人工介入 |

---

## 依赖关系图

```
Phase 1 (基础设施)
  00 ──→ 01 ──→ 02 ──→ 03 ──→ 04 ──→ 05
                                          │
  06 ────────────────────────────────────→│
                                          │
Phase 2 (Auth)                            │
  07 ──→ 08                               │
  09 (RED) ──→ 10 ←──── 04,05,07,08 ─────┘
  11 (RED) ──→ 12 ←──── 04,05,07,08
  13 ←──── 05, 07, 08

Phase 3 (Research 基础设施)
  14 ←──── 02, 05
  15 ←──── 01 (LLM config)
  16 ←──── 03, 06

Phase 4 (Research 业务)
  17 (RED) ──→ 18 ←──── 05, 14, 15
  19 ←──── 05, 14, 15, 16, 18
  20 ←──── 19
  21 ←──── 19, 20
  22 ←──── 14

Phase 5 (Frontend)
  23 ←──── 01 (API base URL config)
  24 ←──── 10, 12 (register/login API available)
  25 ←──── 13 (/me) + 22 (/stats/tokens)
  26 ←──── 18 (POST /new)
  27 ←──── 18 (plan APIs)
  28 ←──── 19 (SSE stream)
  29 ←──── 21 (GET /report)
  30 ←──── 22 (history + delete API)

Phase 6 (集成)
  31 ←──── 全部 Phase 2-5
  32 ←──── 31
```
