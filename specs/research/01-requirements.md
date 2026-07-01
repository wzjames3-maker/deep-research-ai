# 功能需求：核心研究流程

## 来源
PRD.md §4 FR-003 ~ FR-021

## 需求清单

| Spec 需求 ID | PRD 来源 | 描述 | 优先级 |
|---|---|---|---|
| REQ-RES-001 | FR-003 | 发起新研究：输入主题 + 选择模板 → 生成研究计划 | P0 |
| REQ-RES-002 | FR-004, FR-005 | 展示研究计划 + 多轮对话修改 | P0 |
| REQ-RES-003 | FR-006 | 确认研究计划并触发执行 | P0 |
| REQ-RES-004 | FR-003, FR-021 | 研究模板选择（技术调研/竞品分析/论文综述/自定义） | P1 |
| REQ-RES-005 | FR-007 | Sub-agent 并行执行（3-5 个, 各 ≤2 轮循环） | P0 |
| REQ-RES-006 | FR-008 | 实时进度推送（SSE） | P0 |
| REQ-RES-007 | FR-009 | 研究中断与部分结果保存 | P1 |
| REQ-RES-008 | FR-010, FR-011 | Sub-agent 结果汇总为 Markdown 报告 | P0 |
| REQ-RES-009 | FR-012 | 报告引用溯源（点击跳转原始来源） | P1 |
| REQ-RES-010 | FR-014 | 研究历史列表（按时间倒序） | P0 |
| REQ-RES-011 | FR-015 | 研究记录软删除 | P1 |
| REQ-RES-012 | FR-016 | 草稿保存与恢复 | P1 |
| REQ-RES-013 | FR-017 | MCP 协议接入搜索源 | P0 |
| REQ-RES-014 | FR-018 | Sub-agent 搜索 URL 去重 | P0 |
| REQ-RES-015 | FR-019 | Token 消耗统计 | P1 |
| REQ-RES-016 | FR-020 | 重新研究（预填主题） | P2 |
| REQ-RES-017 | FR-013 | 报告复制（纯文本/Markdown） | P1 |

---

## REQ-RES-001: 发起新研究

- **输入**:
  - `topic` : string（必填, 1-500 字符）
  - `template` : enum（必填: tech_research / competitive_analysis / literature_review / custom）
- **输出**: `{ researchId, plan: { subAgents: [{ name, goal, searchDirection }] } }`
- **前置条件**: 已登录, 当前无进行中的研究（RULE-RES-001）
- **后置条件**: 创建 Research 记录（status='draft'），生成研究计划
- **覆盖规则**: RULE-RES-001（单用户并发限制）, RULE-RES-002（模板拆分策略）
- **异常**: EC-RES-001（LLM 超时）, EC-RES-005（并发研究）

## REQ-RES-002: 多轮修改研究计划

- **描述**: 用户可在聊天面板发送修改指令，主 Agent 基于反馈重新生成计划
- **修改轮次上限**: 10 轮（EC-RES-003）
- **输入**: `{ researchId, feedback: string }`
- **输出**: 更新后的研究计划
- **覆盖规则**: RULE-RES-003（修改轮次限制）
- **异常**: EC-RES-001, EC-RES-003

## REQ-RES-003: 确认计划并触发执行

- **描述**: 用户确认后，计划状态从 draft → running（`confirmed` 为瞬态，不持久化），Sub-agent 开始执行
- **输入**: `{ researchId }`
- **输出**: SSE 流开始推送进度
- **覆盖规则**: RULE-RES-004（Sub-agent 分发）

## REQ-RES-005: Sub-agent 并行执行

- **描述**: 3-5 个 Sub-agent 并行运行，每个最多 2 轮搜索循环
- **每轮循环**:
  1. 通过 MCP 调用 Brave Search 获取结果
  2. URL 去重（排除已访问 URL）
  3. LLM 评估信息是否充足
  4. 若不足且未达 2 轮上限 → 生成新搜索词回到步骤 1
  5. 否则 → 输出该子课题的研究发现
- **覆盖规则**: RULE-RES-005（搜索循环）, RULE-RES-006（URL 去重）, RULE-RES-007（信息阈值评估）
- **异常**: EC-RES-002（MCP 不可用）, EC-RES-004（所有 Sub-agent 失败）

## REQ-RES-008: 结果汇总与报告生成

- **描述**: 汇总 Agent 聚合所有 Sub-agent 输出，生成 Markdown 报告
- **报告结构**: ① 研究计划摘要 ② 各 Sub-agent 详细发现 ③ 综合结论与引用
- **输出**: 存入 `Research.report_markdown`，通过 SSE 推送给前端
- **覆盖规则**: RULE-RES-008（汇总策略）
- **异常**: EC-RES-004（全失败拒绝生成）, EC-RES-006（报告超长截断）
