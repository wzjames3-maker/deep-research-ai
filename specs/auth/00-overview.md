# 模块概述：用户认证（auth）

## 来源
PRD.md §1 概述, §2 用户角色, §3 UC-001/UC-002

## 做什么
- 账号密码注册
- 账号密码登录
- JWT Token 签发与验证
- 会话管理（记住我 / 短期Token）
- 登录失败锁定机制

## 不做什么
- ❌ 不做邮箱注册/验证（V1 仅账号+密码）
- ❌ 不做 OAuth/第三方登录
- ❌ 不做密码重置
- ❌ 不做用户资料管理

## 技术栈
| 类别 | 选择 | 引用 |
|---|---|---|
| 框架 | FastAPI | tech-decision.md 决策1 |
| 密码加密 | bcrypt (passlib) | tech-decision.md 决策6 |
| JWT | python-jose[cryptography] | tech-decision.md 决策6 |
| 数据库 | PostgreSQL 16 | tech-decision.md 决策2 |
| ORM | SQLAlchemy 2.0 async | research-report.md 模块6 |

## 决策分类（引用调研报告）
| 组件 | 决策 | 说明 |
|---|---|---|
| FastAPI OAuth2 | ✅ 直接复用 | 框架内置 Bearer 认证 |
| python-jose | ✅ 直接复用 | JWT 签发/验证 |
| passlib[bcrypt] | ✅ 直接复用 | 密码哈希 |
