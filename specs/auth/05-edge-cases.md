# 边界情况与异常处理

## 来源
PRD.md §3 UC-001/UC-002 异常流程

---

## EC-AUTH-001: 并发注册同一账号

- **场景**: 两个请求几乎同时注册同一 username
- **处理**: 依赖数据库 UNIQUE 约束，后到的事务因唯一键冲突返回 409
- **实现**: **禁止** 先 `SELECT` 再 `INSERT`；直接 `INSERT` 并捕获 `IntegrityError`
- **日志**: WARNING 级别

---

## EC-AUTH-002: 密码中含特殊字符

- **场景**: 密码含 `'`, `"`, `\`, `<`, `>` 等
- **处理**: bcrypt 本身安全处理任意字节，无需额外转义
- **日志**: 永远不记录密码原文

---

## EC-AUTH-003: 连续登录失败触发锁定

- **场景**: 用户连续输入错误密码
- **处理**: 见 RULE-AUTH-003
- **日志**: 第 5 次失败时记录 WARNING 日志（含 IP、username、剩余锁定时长）

---

## EC-AUTH-004: 锁定期间用正确密码登录

- **场景**: locked_until 未过期，用户输入正确密码
- **处理**: 返回 423 ACCOUNT_LOCKED，不透露密码是否正确
- **注意**: 不更新 failed_login_count，不解锁

---

## EC-AUTH-005: Token 过期/篡改

- **场景**: JWT exp 已过 或 签名不匹配
- **处理**: 统一返回 401 `{ "code": "TOKEN_INVALID" }`
- **注意**: 不区分"过期"和"篡改"

---

## EC-AUTH-006: JWT_SECRET 未配置

- **场景**: 环境变量 `JWT_SECRET` 为空
- **处理**: 应用启动时检查，若缺失则**拒绝启动**并输出 FATAL 日志

---

## EC-AUTH-007: Password hash 字段长度

- **场景**: bcrypt hash 输出 60 字符，VARCHAR 需留余量
- **处理**: `password_hash` 定义为 VARCHAR(255)

---

## EC-AUTH-008: 单 IP 暴力破解

- **场景**: 同一 IP 大量尝试不同账号或同一账号的密码
- **处理**: Rate Limit 10 次/分钟/IP
- **日志**: 连续触发 rate limit 3 次时记录 WARNING

---

## EC-AUTH-009: 数据库连接失败

- **场景**: PostgreSQL 不可达
- **处理**: 返回 503 `{ "code": "SERVICE_UNAVAILABLE" }`
- **日志**: ERROR 级别含完整堆栈
