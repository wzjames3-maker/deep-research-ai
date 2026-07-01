# 数据模型

## 来源
PRD.md §3 UC-003 ~ UC-009 + tech-decision.md 决策2 (PostgreSQL)

---

## 实体：Research（研究记录）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| user_id | UUID | FK → users.id, NOT NULL | 所属用户 |
| topic | VARCHAR(500) | NOT NULL | 研究主题 |
| template | research_template | NOT NULL | 拆分模板类型 |
| status | research_status | NOT NULL, DEFAULT 'draft' | draft/confirmed/running/completed/failed/cancelled |
| plan_json | JSONB | NULLABLE | 研究计划（Sub-agent 清单+各自目标） |
| report_markdown | TEXT | NULLABLE | 最终 Markdown 报告 |
| total_tokens | INTEGER | NOT NULL, DEFAULT 0 | 累计 Token 消耗 |
| error_message | TEXT | NULLABLE | 失败原因（status='failed' 时） |
| deleted_at | TIMESTAMPTZ | NULLABLE | 软删除时间（NULL=未删除） |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| started_at | TIMESTAMPTZ | NULLABLE | 开始执行时间 |
| completed_at | TIMESTAMPTZ | NULLABLE | 完成时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 更新时间 |

### ENUM: research_template
```sql
CREATE TYPE research_template AS ENUM (
  'tech_research',        -- 技术调研
  'competitive_analysis',  -- 竞品分析
  'literature_review',     -- 论文综述
  'custom'                 -- 自定义
);
```

### ENUM: research_status
```sql
CREATE TYPE research_status AS ENUM (
  'draft',       -- 计划生成中/讨论中
  'confirmed',   -- 计划已确认，待执行（瞬态，V1 不持久化，仅用于 SSE 事件通知；confirm API 直接写入 'running'）
  'running',     -- Sub-agent 执行中
  'completed',   -- 成功完成
  'failed',      -- 执行失败
  'cancelled'    -- 用户取消
);
```

> **注意**: `confirmed` 在 V1 中为瞬态，数据库中不会实际存储该状态。`POST /plan/confirm` 接口直接将状态从 `draft` 写入 `running`，并通过 SSE `plan_confirm` 事件通知前端。保留该 ENUM 值仅为未来扩展预留（如需异步确认场景）。详见 `research/04-business-rules.md` RULE-RES-004。

---

## 实体：SubAgentResult（Sub-agent 执行结果）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| research_id | UUID | FK → researches.id, NOT NULL | 所属研究 |
| agent_name | VARCHAR(200) | NOT NULL | Sub-agent 名称 |
| agent_goal | TEXT | NOT NULL | Sub-agent 目标描述 |
| search_direction | TEXT | NOT NULL | 搜索方向 |
| status | sub_agent_status | NOT NULL, DEFAULT 'pending' | pending/running/completed/failed/cancelled |
| rounds_completed | INTEGER | NOT NULL, DEFAULT 0 | 已完成的搜索轮次 |
| visited_urls | JSONB | NOT NULL, DEFAULT '[]' | 已访问 URL 列表（去重用） |
| findings_text | TEXT | NULLABLE | 研究发现（Markdown），API 返回字段名 `findings` |
| token_used | INTEGER | NOT NULL, DEFAULT 0 | 本 Sub-agent 消耗的 Token |
| error_message | TEXT | NULLABLE | 失败原因 |
| started_at | TIMESTAMPTZ | NULLABLE | 开始时间 |
| completed_at | TIMESTAMPTZ | NULLABLE | 完成时间 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |

### ENUM: sub_agent_status
```sql
CREATE TYPE sub_agent_status AS ENUM (
  'pending',     -- 等待执行
  'running',     -- 执行中
  'completed',   -- 成功完成
  'failed',      -- 执行失败
  'cancelled'    -- 被取消
);
```

---

## 实体：ResearchPlanFeedback（计划讨论记录）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| research_id | UUID | FK → researches.id, NOT NULL | 所属研究 |
| round | INTEGER | NOT NULL | 第几轮修改 |
| user_feedback | TEXT | NOT NULL | 用户修改意见 |
| plan_snapshot | JSONB | NOT NULL | 该轮生成的计划快照 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |

---

## 索引

| 名称 | 字段 | 类型 | 说明 |
|---|---|---|---|
| idx_research_user_id | (user_id, created_at DESC) | BTREE | 按用户查询研究历史 |
| idx_research_status_user | (user_id, status) | BTREE | 查询进行中的研究（并发检查） |
| idx_research_deleted_at | (deleted_at) | BTREE | 软删除过滤（WHERE deleted_at IS NULL） |
| idx_sub_agent_research_id | (research_id) | BTREE | 查询某研究的 Sub-agent 结果 |

## Migration 注意事项

- `Research.updated_at` 和 `SubAgentResult.created_at` 等时间字段需复用 auth 模块的 `update_updated_at_column()` trigger（或为各表单独创建）
- 所有 `TIMESTAMPTZ` 字段统一使用带时区的时间戳

---

## ER 关系

```
User (auth) 1 ──── N Research
Research   1 ──── N SubAgentResult
Research   1 ──── N ResearchPlanFeedback
```

---

## 软删除说明

- `Research.deleted_at` 为软删除标记
- 所有查询默认加 `WHERE deleted_at IS NULL`
- 删除操作：`UPDATE researches SET deleted_at = NOW()`（不执行物理 DELETE）
- SubAgentResult 和 ResearchPlanFeedback 不独立软删除（跟随 Research 的 deleted_at）
