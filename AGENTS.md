# SDD Workflow — Agent Global Index

> Spec-Driven Development for AI Agent Development
> 本文件是 Agent 每次启动时第一个加载的全局索引。只包含路由信息和全局规则，详细 SOP 在各阶段文件中。

---

## Core Principles

- **人管 spec，Agent 管代码** — 人的精力花在 spec 上，代码交给 Agent
- **每一步都有冻结点** — 前一步不通过不进下一步
- **Agent 永远引用 spec 条目** — 不允许"自由发挥"
- **变更从 spec 开始** — 需求变了先改 spec，再让 Agent 重新执行

---

## v2 Iteration Principle

> **铁律：不要去修改 Agent 生成的代码，而是去修改驱动 Agent 的那 8 层 Spec。**
> Spec 的修改和代码的修改绑定在同一个 Git 分支里。

代码是 Spec 的投影，修改投影不如修改光源。

---

## Flow Overview

```
Phase 0    Problem Statement（问题定义）        人         problem-statement.md
Phase 1    需求收集与澄清                       人+AI      requirements-raw.md
Phase 2    可行性分析                           人+AI      feasibility.md
Phase 3    PRD 编写与评审                       人+AI      PRD.md（冻结）
Phase 3.1  开源生态调研                         人+AI      research-report.md
Phase 3.2  UI/UX 设计与资产化（有前端时必做）    人+AI      design/ 目录
Phase 3.5  技术选型（架构级）                    人+AI      tech-decision.md（冻结）
Phase 4    Spec 编写（8 层文件）                 人+AI      specs/module/00~08.md
Phase 5    Spec 评审与冻结                       人         spec 基线 v1.0
Phase 6    任务拆分与检查点设计                  人+AI      tasks/ + 验收检查点
Phase 7    Agent 逐任务执行（串行门控）            AI         代码 + 检查点报告
Phase 8    逐任务验收（人确认检查点）               人         验收记录
Phase 9    集成验收                             人+AI      集成验收报告
Phase 10   交付与发布                           人+AI      线上版本 + 归档 spec
```

---

## Core Logic Chain

```
问题定义（要解决什么）
    ↓
需求收集与澄清（具体要做什么）
    ↓
可行性分析（能不能做）→ 初步技术方向（供调研假设）→ 人判定（Go/No-Go）
    ↓
PRD（做什么）→ 定义业务需求、用例、非功能指标
    ↓
开源生态调研（有没有现成的）→ 搜索 GitHub/社区，评估可复用方案
    ↓
UI/UX 设计（长什么样）→ 交互稿、设计资产、Design Tokens（有前端时必做）
    ↓
技术选型（用什么做）→ 基于 PRD 需求 + 调研结论 + UI 复杂度 来选技术方案
    ↓
Spec（怎么做）→ 基于已选定的技术方案编写实现规约，复用部分直接引用
    ↓
Task（拆成 Agent 可执行的单元）
    ↓
Agent 执行 → 逐任务验收 → 集成验收 → 交付
```

---

## Why This Order

- PRD 描述的是业务需求和用例，不应该依赖技术方案
- PRD 里的非功能需求（QPS、可用性、数据量）是技术选型的**输入**
- PRD 里的功能需求（事务、一致性、实时性）决定技术方案的**选择范围**
- 开源生态调研在 PRD 之后，因为需要知道"要做什么"才能有针对性地搜索现成方案
- 调研结论会反向约束技术选型（如选了 Cytoscape.js 的 React 封装 → 前端必须用 React）
- UI/UX 设计也会约束技术选型：复杂的交互动画 → 可能排除 SSR 框架；设计系统中组件复杂度 → 影响组件库选择
- 技术选型是「PRD 的需求 + 调研结论 + UI/UX 设计 → 技术方案」的映射，不是反过来
- 比如：PRD 要求「注册和日志写入必须原子性」→ 这个需求驱动选 PostgreSQL 而不是 MongoDB

---

## Global Constraints (跨阶段生效)

1. **人管 spec，Agent 管代码** — 代码由 Agent 生成，人只审 spec
2. **串行门控** — 一次只执行一个任务，过检查点才进下一个
3. **容器内执行** — 所有测试/lint/构建在 docker compose 容器内运行，禁止依赖宿主机
4. **断路器** — 同一任务修复 ≤ 3 次，超限 → BLOCKED，人介入
5. **TDD 模式** — 测试任务和实现任务分离，测试先行
6. **测试数据隔离** — 每个测试用例必须有独立的 beforeEach / afterEach
7. **Migration 前置** — 涉及 data-model 变更的任务，前置必须是容器内真实执行的 Migration
8. **改 Spec 不改代码** — 迭代时修改 Spec，让 Agent 重新生成代码，spec + code 同 Git 分支

---

## Phase Routing (阶段路由)

> 读取本文件后，根据当前阶段加载对应文件。不要一次加载全部。
> 读取本文件后，根据当前阶段加载对应文件。不要一次加载全部。
> 读取本文件后，根据当前阶段加载对应文件。不要一次加载全部。

### First-pass Flow (Phase 0 -> 10)

| Phase | Load File | Artifact Template | Checklist |
|---|---|---|---|
| Phase 0 | phases/phase-0-problem.md | artifacts/problem-statement.md | checklists/checklist-phase-0.md |
| Phase 1 | phases/phase-1-requirements.md | artifacts/requirements-raw.md | checklists/checklist-phase-1.md |
| Phase 2 | phases/phase-2-feasibility.md | artifacts/feasibility.md | checklists/checklist-phase-2.md |
| Phase 3 | phases/phase-3-prd.md | artifacts/prd.md | checklists/checklist-phase-3.md |
| Phase 3.1 | phases/phase-3.1-research.md | artifacts/research-report.md | checklists/checklist-phase-3.1.md |
| Phase 3.2 | phases/phase-3.2-design.md | artifacts/design-tokens.json | checklists/checklist-phase-3.2.md |
| Phase 3.5 | phases/phase-3.5-tech-selection.md | artifacts/tech-decision.md | checklists/checklist-phase-3.5.md |
| Phase 4 | phases/phase-4-spec.md | artifacts/spec-00~08.md | checklists/checklist-phase-4.md |
| Phase 5 | phases/phase-5-review.md | - | checklists/checklist-phase-5.md |
| Phase 6 | phases/phase-6-task-split.md | artifacts/task-file.md + checkpoint.md + task-board.md | checklists/checklist-phase-6.md |
| Phase 7 | phases/phase-7-execution.md | - | checklists/checklist-phase-7.md |
| Phase 8 | phases/phase-8-acceptance.md | - | checklists/checklist-phase-8.md |
| Phase 9 | phases/phase-9-integration.md | - | checklists/checklist-phase-9.md |
| Phase 10 | phases/phase-10-delivery.md | - | checklists/checklist-phase-10.md |

### Iteration Paths

| Tier | Load File | Checklist |
|---|---|---|
| S (Hotfix) | tiers/tier-s-hotfix.md | checklists/checklist-tier-s.md |
| M (Enhance) | tiers/tier-m-enhance.md | checklists/checklist-tier-m.md |
| L (New Module) | tiers/tier-l-new-module.md | checklists/checklist-tier-l.md |

---

## v2 Iteration Methodology

### Decision Tree

```
变更需求进来
    │
    ├─ 只影响 1-2 个 Spec 文件，不涉及新接口/新实体？
    │     └─ → Tier S（轻量修复）
    │
    ├─ 在已有模块内增加新特性，有新增接口/字段/实体？
    │     └─ → Tier M（模块增强）
    │
    └─ 引入全新模块，或底层架构替换？
          └─ → Tier L（全新模块）
```

### Git Branch Convention

每次迭代（无论哪个 Tier）都遵循：
- Spec 变更和代码变更在**同一个 feature 分支**里提交
- 分支命名：`iter/{tier}-{简述}`
  - `iter/s-fix-lock-threshold`
  - `iter/m-phone-login`
  - `iter/l-payment-module`
- PR 中同时包含 Spec diff 和 Code diff，reviewer 可以对照审查

### 3-Tier Comparison

| Dimension | Tier S | Tier M | Tier L |
|---|---|---|---|
| Entry Phase | Phase 5 | Phase 3 | Phase 0 / 1 |
| Typical Duration | 0.5 ~ 1 day | 1 ~ 3 days | 1 ~ 3 weeks |
| Spec Change Scope | 1-2 files | 3-5 files | Full 8-layer files |
| PRD Updated | No | Incremental | Full rewrite |
| Tech Selection Redone | No | Quick confirm | Full evaluation |
| New specs/ Directory | No | No (update existing) | Yes (independent) |
| New tasks/ Phase | hotfix-xxx.md | phase-N-vX.X/ | phase-N-{module}/ |
| Integration Testing | Affected AC regression | Module-level regression | Cross-module E2E |

---

## Project Directory Structure

```
project/
├── AGENTS.md                      # Agent 全局行为约束（本文件）
├── docs/
│   ├── problem-statement.md       # Phase 0
│   ├── requirements-raw.md        # Phase 1
│   ├── feasibility.md             # Phase 2
│   ├── PRD.md                     # Phase 3（冻结）
│   ├── research-report.md         # Phase 3.1
│   └── tech-decision.md           # Phase 3.5（冻结）
├── design/
│   ├── user-flows.md              # Phase 3.2
│   ├── design-tokens.json         # Phase 3.2
│   ├── pages/
│   │   └── ...
│   └── components/
│       └── ...
├── specs/
│   ├── auth/
│   │   ├── 00-overview.md         # Phase 4
│   │   ├── 01-requirements.md
│   │   ├── 02-data-model.md
│   │   ├── 03-api-contract.md
│   │   ├── 04-business-rules.md
│   │   ├── 05-edge-cases.md
│   │   ├── 06-acceptance.md
│   │   ├── 07-tech-constraints.md
│   │   └── 08-dependencies.md
│   └── ...
├── tasks/
│   ├── task.md                    # 总进度看板
│   ├── phase-1/                   # 跨模块基础设施
│   ├── phase-2/                   # 核心功能模块
│   ├── phase-3/                   # 测试与监控
│   └── phase-4/                   # 交付收尾
├── src/                           # Agent 生成的代码（Phase 7）
├── tests/                         # 测试代码
└── CHANGELOG.md                   # 变更记录
```

---

## Participants & Artifacts Summary

| Phase | Task | Participants | Agent Role | Core Artifact | Frozen |
|---|---|---|---|---|---|
| 0 | Problem Definition | Product/Tech Lead | No | problem-statement.md | - |
| 1 | Requirements | Product+Tech+Biz | Assist | requirements-raw.md | - |
| 2 | Feasibility | Tech Lead+Architect | Assist | feasibility.md | - |
| 3 | PRD | Product+Tech+Biz | Assist | PRD.md | Frozen |
| 3.1 | OSS Research | Tech Lead+Dev | High Assist | research-report.md | - |
| 3.2 | UI/UX Design | Designer+Frontend | Assist | design/ directory | - |
| 3.5 | Tech Selection | Architect+Tech Lead | Assist | tech-decision.md | Frozen |
| 4 | Spec Writing | Tech Lead+Dev | Assist | specs/ 00~08.md | - |
| 5 | Spec Review | Full Tech Team | No | spec baseline v1.0 | Frozen |
| 6 | Task Splitting | Tech Lead | Assist | tasks/ directory | - |
| 7 | Agent Execution | Dev monitors | Primary | Code + reports | - |
| 8 | Task Acceptance | Dev/Test | No | Acceptance records | - |
| 9 | Integration | Tech+Test | Assist | Integration report | - |
| 10 | Delivery | All | Assist | Release + archived spec | - |
