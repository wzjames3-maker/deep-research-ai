# Task 02: 数据库 Migration

## 对应 Spec
- specs/auth/02-data-model.md（User 表）
- specs/research/02-data-model.md（Research, SubAgentResult, ResearchPlanFeedback 表）
- spec汇总.md §四 数据模型汇总（ER 图 + 字段说明）

## 输入文件（Agent 需读取）
- specs/auth/02-data-model.md
- specs/research/02-data-model.md
- spec汇总.md §四（完整 ER 图参考）
- `src/models/base.py`（Base 类定义，Task 01 产出）
- `alembic.ini`（Alembic 配置，Task 01 产出）

## 输出文件
- `src/models/user.py`（User SQLAlchemy 模型）
- `src/models/research.py`（Research 模型）
- `src/models/sub_agent_result.py`（SubAgentResult 模型）
- `src/models/research_plan_feedback.py`（ResearchPlanFeedback 模型）
- `alembic/versions/001_initial_schema.py`（初始 Migration 脚本）

## 前置任务
- Task 01（项目骨架，提供 Base 类和 Alembic 配置）
- Task 00（容器环境，提供 PostgreSQL）

## 实现要求
1. **4 张实体表** 严格按照 data-model spec 实现：

### Users 表
| 字段 | 类型 | 约束 |
|---|---|---|
| id | UUID | PK, server_default=uuid4 |
| username | String(50) | UNIQUE, lowercase 存储 |
| password_hash | String(255) | NOT NULL |
| status | Enum(user_status) | default='active' |
| failed_login_count | Integer | default=0 |
| locked_until | DateTime(TZ) | nullable |
| remember_me | Boolean | default=False |
| created_at | DateTime(TZ) | default=now |
| updated_at | DateTime(TZ) | default=now, onupdate=now |

### Researches 表
| 字段 | 类型 | 约束 |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| topic | String(500) | NOT NULL |
| template | Enum(research_template) | NOT NULL |
| status | Enum(research_status) | default='draft' |
| plan_json | JSONB | nullable |
| report_markdown | Text | nullable |
| total_tokens | Integer | default=0 |
| error_message | Text | nullable |
| deleted_at | DateTime(TZ) | nullable (软删除) |
| created_at | DateTime(TZ) | default=now |
| started_at | DateTime(TZ) | nullable |
| completed_at | DateTime(TZ) | nullable |
| updated_at | DateTime(TZ) | default=now, onupdate=now |

### SubAgentResults 表
| 字段 | 类型 | 约束 |
|---|---|---|
| id | UUID | PK |
| research_id | UUID | FK → researches.id, NOT NULL |
| agent_name | String(200) | NOT NULL |
| agent_goal | Text | NOT NULL |
| search_direction | Text | NOT NULL |
| status | Enum(sub_agent_status) | default='pending' |
| rounds_completed | Integer | default=0 |
| visited_urls | JSONB | default=[] |
| findings_text | Text | nullable |
| token_used | Integer | default=0 |
| error_message | Text | nullable |
| started_at | DateTime(TZ) | nullable |
| completed_at | DateTime(TZ) | nullable |
| created_at | DateTime(TZ) | default=now |

### ResearchPlanFeedbacks 表
| 字段 | 类型 | 约束 |
|---|---|---|
| id | UUID | PK |
| research_id | UUID | FK → researches.id, NOT NULL |
| round | Integer | NOT NULL |
| user_feedback | Text | NOT NULL |
| plan_snapshot | JSONB | NOT NULL |
| created_at | DateTime(TZ) | default=now |

2. **4 个 ENUM 类型**:
   - `user_status`: active, locked
   - `research_template`: tech_research, competitive_analysis, literature_review, custom
   - `research_status`: draft, confirmed, running, completed, failed, cancelled
   - `sub_agent_status`: pending, running, completed, failed, cancelled

3. **Migration 必须**:
   - 在容器内真实执行: `docker compose exec app alembic upgrade head`
   - 包含所有 4 张表的 CREATE TABLE + 4 个 ENUM 的 CREATE TYPE
   - 外键约束 + CASCADE DELETE（researches 删除时级联删除 sub_agent_results 和 plan_feedbacks）
   - `researches.deleted_at` 上建部分索引 `WHERE deleted_at IS NULL`（索引未删除记录，高频查询）
   - 4 个索引（必须创建）:
     - `idx_research_user_id ON researches (user_id, created_at DESC)` — 用户历史查询
     - `idx_research_status_user ON researches (user_id, status)` — 并发检查
     - `idx_research_deleted_at ON researches (deleted_at) WHERE deleted_at IS NULL` — 软删除过滤
     - `idx_sub_agent_research_id ON sub_agent_results (research_id)` — Sub-agent 结果查询

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 01 产出文件 `src/models/base.py` 存在
- [ ] Alembic 已初始化（`alembic.ini` + `alembic/` 目录存在）
- [ ] PostgreSQL 容器正在运行并可连接

### Migration 验证
- [ ] `docker compose exec app alembic upgrade head` 执行成功（无报错）
- [ ] `docker compose exec app alembic downgrade -1` 回滚成功
- [ ] `docker compose exec db psql -U user -d deepresearch -c "\dt"` 列出 4 张表
- [ ] `docker compose exec db psql -U user -d deepresearch -c "\dT+"` 列出 4 个 ENUM

### Schema 一致性
- [ ] 每张表字段名、类型与 spec 一致（`\d+ 表名` 逐一比对）
- [ ] UUID 主键使用 `gen_random_uuid()` 作为默认值
- [ ] `created_at` / `updated_at` 使用 `TIMESTAMPTZ`
- [ ] `deleted_at` 允许 NULL
- [ ] 外键约束存在: researches.user_id → users.id, sub_agent_results.research_id → researches.id, research_plan_feedbacks.research_id → researches.id
- [ ] 4 个索引全部创建（`\di` 列出所有索引）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 03
