# 技术约束

## 架构级约束（引用 tech-decision.md）

| 决策 | 引用 |
|---|---|
| 后端语言 | Python 3.12+ | tech-decision.md 决策1 |
| Web 框架 | FastAPI | tech-decision.md 决策1 |
| 数据库 | PostgreSQL 16 | tech-decision.md 决策2 |
| 认证方案 | JWT (HS256) | tech-decision.md 决策6 |
| 部署 | Docker Compose | tech-decision.md 决策8 |

## 实现级选型

| 类别 | 包名 | 版本 | 理由 |
|---|---|---|---|
| 密码加密 | `passlib[bcrypt]` | ^1.7.4 | Python 密码哈希标准库 |
| JWT | `python-jose[cryptography]` | ^3.3.0 | JWT 签发/验证 |
| 入参校验 | `pydantic` | ^2.x | FastAPI 内置，类型安全 |
| 速率限制 | `slowapi` | ^0.1.9 | FastAPI 兼容的 rate limiter |
| 数据库驱动 | `asyncpg` | ^0.29.0 | PostgreSQL async 驱动 |
| ORM | `sqlalchemy[asyncio]` | ^2.0.51 | Async ORM 标准 |

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| `JWT_SECRET` | 是 | JWT 签名密钥，≥ 32 字符 |
| `DATABASE_URL` | 是 | PostgreSQL 连接串，格式 `postgresql+asyncpg://user:pass@host:5432/db` |
| `BCRYPT_ROUNDS` | 否 | bcrypt cost factor，默认 12 |

## 性能要求

- 注册/登录接口: P99 < 200ms（不含数据库网络延迟）
- bcrypt cost = 12 时哈希耗时 ~250ms（在 `ThreadPoolExecutor` 中执行，不阻塞事件循环）

## 禁止使用

- 禁止在日志中输出密码原文或 password_hash
- 禁止在 JWT payload 中包含敏感信息
- 禁止使用 `python-jose` 的 `none` 算法
