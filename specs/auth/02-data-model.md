# 数据模型

## 来源
PRD.md §3 UC-001/UC-002 + tech-decision.md 决策2 (PostgreSQL)

## 实体：User

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号，字母数字下划线 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash (cost=12) |
| status | user_status | NOT NULL, DEFAULT 'active' | active / locked |
| failed_login_count | INT | NOT NULL, DEFAULT 0 | 连续登录失败次数 |
| locked_until | TIMESTAMPTZ | NULLABLE | 锁定截止时间 |
| remember_me | BOOLEAN | NOT NULL, DEFAULT false | 上次登录是否勾选记住我 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 更新时间 |

### ENUM: user_status
```sql
CREATE TYPE user_status AS ENUM ('active', 'locked');
```

## 索引

| 名称 | 字段 | 类型 | 说明 |
|---|---|---|---|
| idx_user_username | username | UNIQUE | 登录/注册查询 |
| idx_user_status | status | BTREE | 过滤活跃用户 |

## Migration 注意事项

- `username` 存储前必须 `.strip().lower()`（大小写不敏感 + 去空白）
- `updated_at` 需创建 trigger 自动更新
- username UNIQUE 约束在 lowercase 后的值上生效
