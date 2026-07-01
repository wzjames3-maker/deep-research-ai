# 功能需求：用户认证

## 来源
PRD.md §4 功能需求 FR-001, FR-002

## 需求清单

| Spec 需求 ID | PRD 来源 | 描述 | 优先级 |
|---|---|---|---|
| REQ-AUTH-001 | FR-001 | 账号密码注册 | P0 |
| REQ-AUTH-002 | FR-001 | 账号密码登录（含锁定） | P0 |
| REQ-AUTH-003 | FR-002 | JWT 签发与 Token 刷新 | P0 |

---

## REQ-AUTH-001: 账号密码注册

- **输入**:
  - `username` : string（必填, 3-50 字符，仅允许字母数字和下划线）
  - `password` : string（必填, 8-64字符, 至少1字母+1数字）
- **输出**: `{ userId, username, token, expiresIn }`
- **前置条件**: 无（匿名用户可访问）
- **后置条件**: 创建 User 记录, password 以 bcrypt hash 存储, 自动登录返回 JWT
- **覆盖规则**: RULE-AUTH-001（密码加密）, RULE-AUTH-005（账号规范化）
- **异常**: 见 05-edge-cases.md EC-AUTH-001, EC-AUTH-002

## REQ-AUTH-002: 账号密码登录

- **输入**:
  - `username` : string（必填）
  - `password` : string（必填）
  - `rememberMe` : boolean（选填, default false）
- **输出**: `{ userId, username, token, expiresIn }`
- **前置条件**: 用户已注册且账号未锁定
- **后置条件**: 返回有效 JWT；若 rememberMe=true, Token 有效期 7 天；否则 24 小时
- **覆盖规则**: RULE-AUTH-002（JWT签发）, RULE-AUTH-003（登录失败锁定）, RULE-AUTH-004（登录成功重置）
- **异常**: 见 05-edge-cases.md EC-AUTH-003, EC-AUTH-004

## REQ-AUTH-003: JWT 签发与会话管理

- **描述**: 所有需要认证的 API 请求必须携带 Authorization: Bearer <token> 头
- **验证规则**:
  - Token 签名用 HS256 算法验证
  - Token 过期返回 401
  - 返回 TOKEN_INVALID
- **Token 生命周期**:
  - 短期 Token: 24 小时
  - 记住我 Token: 7 天
- **覆盖规则**: RULE-AUTH-002
- **异常**: 见 05-edge-cases.md EC-AUTH-005
