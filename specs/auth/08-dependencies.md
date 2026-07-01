# 依赖关系

## 前置依赖

- 无（auth 是基础模块，其他模块依赖它）

## 后置依赖

| 依赖方模块 | 依赖内容 | 使用方式 |
|---|---|---|
| research | JWT 认证中间件 | 通过 FastAPI `Depends(get_current_user)` 注入 `current_user` |
| research | User 模型 | 获取 userId、username 以关联研究记录 |
| frontend | Auth API | 调用 `/api/v1/auth/register`、`/login`、`/me`、`/refresh`、`/ticket` |

## 对外接口

| 接口 | 类型 | 用途 |
|---|---|---|
| `get_current_user()` | FastAPI Dependency | 从 Bearer token 解析并验证当前用户，返回 User ORM 对象 |
| `User` ORM Model | SQLAlchemy Model | 其他模块通过此 Model 查询/关联用户数据 |

## 数据库对象

| 对象 | 类型 | 所有模块 |
|---|---|---|
| `users` | TABLE | auth |
| `user_status` | ENUM | auth |
| `update_updated_at_column()` | FUNCTION | auth（可被其他模块复用） |
