# Task 24: 登录/注册页面

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-001
- specs/frontend/06-acceptance.md AC-FE-001, 002, 016
- specs/frontend/04-business-rules.md RULE-FE-001, 002

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md（AC-FE-001, 002, 016）
- frontend/src/api/auth.ts（login, register API）
- frontend/src/contexts/AuthContext.tsx（认证状态）

## 输出文件
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/RegisterPage.tsx`
- `frontend/src/components/LoginForm.tsx`
- `frontend/src/components/RegisterForm.tsx`

## 前置任务
- Task 23（前端项目骨架 + AuthContext + API 封装）
- Task 12（login API 可用用于测试）
- Task 10（register API 可用用于测试）

## 实现要求

### LoginPage:
- **路径**: `/login`
- **组件树**: `LoginPage > { HeroSection, LoginForm }`
- **Layout**: 居中卡片, 左半桌面图标 + 右半表单

### LoginForm:
- 输入: username (text), password (password), rememberMe (checkbox)
- 提交 → `auth.login(username, password, rememberMe)`
- Loading: 按钮禁用 + spinner
- 错误提示: toast 展示（账号或密码错误 / 账户已锁定 / 过于频繁）
- 成功后: `navigate("/dashboard")`
- 链接: "没有账号？去注册" → `/register`

### RegisterPage:
- **路径**: `/register`

### RegisterForm:
- 输入: username, password, confirmPassword
- 前端校验（RULE-FE-001）:
  - username: 3-50 字符, 仅 `[a-zA-Z0-9_]`, 输入时实时反馈
  - password: 8-64 字符, 至少 1 字母 + 1 数字
  - confirmPassword === password
- 不符合规则 → 输入框下方红色提示, 按钮禁用
- 提交 → `auth.register(username, password)`
- Loading + 错误 toast
- 成功后: 自动登录 → `navigate("/dashboard")`
- 链接: "已有账号？去登录" → `/login`

### 共享样式:
- 使用 shadcn/ui 组件: `Card`, `Input`, `Button`, `Checkbox`, `Label`
- 使用 Tailwind: 居中卡片 `max-w-md mx-auto mt-20`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 23 前端骨架启动正常（npm run dev）
- [ ] 后端 /auth/register 和 /auth/login 接口可用

### AC 验收
- [ ] AC-FE-001: 正确登录 → loading → 跳转 /dashboard, localStorage 有 token
- [ ] AC-FE-002: username="ab", password="123" → 前端校验拦截, 未发送网络请求
- [ ] AC-FE-016: 账号锁定状态 → 42X → toast "账户已锁定"

### 功能验收
- [ ] 登录失败 toast 展示后端错误消息
- [ ] 注册成功自动跳转, 无需再次登录
- [ ] /login 和 /register 是公开页面（无需登录即可访问）
- [ ] 已登录用户访问 /login → 自动重定向到 /dashboard

### 代码质量
- [ ] 使用 shadcn/ui 组件（不是原生 HTML 组件）
- [ ] 表单校验在前端和后端都执行（双重保障）
- [ ] 禁止表单重复提交（debounce + loading 状态）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 25
