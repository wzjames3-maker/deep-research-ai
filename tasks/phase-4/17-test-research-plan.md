# Task 17: 研究计划 — 测试 (TDD: RED)

> **TDD 模式**: 本任务仅生成测试文件。由于业务代码尚未实现，测试执行后应全部 **RED**。

## 对应 Spec
- specs/research/03-api-contract.md:
  - API-RES-001 (POST /new)
  - API-RES-002 (POST /revise)
  - API-RES-003 (POST /confirm)
  - API-RES-005 (GET /{id})
- specs/research/06-acceptance.md AC-RES-001, 002, 003, 004, 005, 006, 019, 022, 023

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md（API-RES-001, 002, 003, 005）
- specs/research/06-acceptance.md（AC-RES-001 ~ 004, 006, 019, 022, 023）
- specs/research/04-business-rules.md（RULE-RES-001~004）
- specs/research/05-edge-cases.md（EC-RES-001, 003, 005）
- tests/conftest.py

## 输出文件
- `tests/research/test_plan.py`（研究计划相关测试）

## 前置任务
- Task 12（login 接口可用，可获取 Token 供测试）
- Task 14（Research 模型 + Repository 可用）
- Task 15（LLM 服务可用）
- Task 05（get_current_user 可用）

## 实现要求
1. **测试数据隔离**: 每个测试通过 register + login 获取 Token，创建/清理独立的测试研究。

2. **测试用例清单**:

| 测试用例 | 覆盖 AC | 描述 |
|---|---|---|
| `test_create_research_success` | AC-RES-001 | 正常发起 → 201, plan.subAgents ∈ [3,5], status='draft' |
| `test_create_research_concurrent_rejected` | AC-RES-002 | 已有 running 的研究 → 409 RESEARCH_IN_PROGRESS |
| `test_create_research_llm_timeout` | AC-RES-019 | LLM 超时 30 秒 → 500 PLAN_GENERATION_FAILED |
| `test_revise_plan_success` | AC-RES-003 | 反馈修改 → 200, planRound 递增, plan 更新 |
| `test_revise_plan_too_many` | AC-RES-004 | 第 11 次修改 → 400 TOO_MANY_REVISIONS |
| `test_revise_plan_not_draft` | — | status≠'draft' 时修改 → 400 INVALID_STATUS |
| `test_confirm_plan_success` | AC-RES-005 | status='draft' → POST confirm → 200, status='running' |
| `test_confirm_plan_not_draft` | — | 非 draft 状态确认 → 400 INVALID_STATUS |
| `test_get_research_detail_draft` | AC-RES-022 | status='draft' → GET /{id} → 含 plan, planRound |
| `test_get_research_detail_running` | AC-RES-023 | status='running' → GET /{id} → 含 subAgentResults |
| `test_get_research_not_found` | — | 不存在/已删除 → 404 |
| `test_get_research_unauthorized` | — | 访问他人研究 → 403 |
| `test_draft_recovery` | AC-RES-006 | status='draft' 的研究可获取并恢复 |

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 12 login 接口可用
- [ ] Task 14 Research model/repo 可用
- [ ] Task 15 LLM 服务可 mock（测试中使用 mock 避免真实 LLM 调用）

### AC 验收
- [ ] 所有测试用例覆盖 AC-RES-001, 002, 003, 004, 006, 019, 022, 023
- [ ] 执行 `pytest tests/ -k test_plan -v` → 全部 RED

### 测试隔离验证
- [ ] 每个测试独立创建自己的研究（通过 API）
- [ ] afterEach 清理测试数据（软删除或物理删除）
- [ ] 测试间不共享 Mock 状态

### 通过判定
全部 ✅ → 任务状态标记为 🔴 **RED** → 进入 Task 18（实现）
