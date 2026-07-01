# 业务规则（前端）

## 来源
PRD.md §3 用例流程 + 技术判断

---

## RULE-FE-001: 表单校验（客户端）

- **触发**: 登录/注册/新建研究表单提交
- **规则**:
  - 账号格式: 3-50 字符，仅允许字母、数字、下划线 `/^[a-zA-Z0-9_]{3,50}$/`
  - 密码校验: 8-64 字符，至少 1 字母 + 1 数字
    - 长度: `password.length >= 8 && password.length <= 64`
    - 包含字母: `/[A-Za-z]/.test(password)`
    - 包含数字: `/[0-9]/.test(password)`
    - 客户端校验仅作为 UX 优化，服务端以 `auth/04-business-rules.md` RULE-AUTH-006 为准
  - 研究主题: 1-500 字符，实时显示剩余字数
- **注意**: 客户端校验只是UX优化，不可替代服务端校验

---

## RULE-FE-002: Token 过期处理

- **触发**: API 返回 401
- **规则**:
  1. 清除 localStorage 中的 token
  2. 跳转到 `/login` 页面
  3. 展示 toast: "登录已过期，请重新登录"
- **不处理**: 403 (无权限) → 展示错误页面

---

## RULE-FE-003: SSE 连接管理

- **触发**: 进入 `/research/{id}` 页面（status='running' 时渲染 ProgressDashboard 子视图）
- **规则**:
  1. 组件 mount → 创建 `EventSource(sseUrl)`
  2. 组件 unmount → `eventSource.close()`
  3. 断线重连: EventSource 原生自动重连，若 30 秒内未恢复 → 展示"连接中断"提示
  4. 页面隐藏/后台: 不关闭 SSE（可见性变化 API 可暂停 UI 渲染但不断开）
- **事件处理**:
  - 每个 event type 对应一个 handler 更新状态
  - `report_complete` → 自动切换到 ReportView 子视图（URL 不变，状态驱动）

---

## RULE-FE-004: 空状态展示

- **触发**: 研究历史列表为空
- **规则**: 展示插图和文案"还没有研究记录，去发起第一个研究吧"，附带"新建研究"按钮
- **触发**: Sub-agent 结果为空 → 展示"暂无结果"

---

## RULE-FE-005: 按钮状态管理

- **触发**: 异步操作期间
- **规则**:
  - 提交中 → loading spinner + 禁用按钮（防止重复提交）
  - 成功 → 执行后续操作（跳转/刷新列表）
  - 失败 → 展示错误提示 + 恢复按钮
  - 停止研究 → loading 状态 + 确认后标志位切换
- **防抖**: 研究计划修改频繁 → 提交按钮无防抖（立即发送）；"确认计划"按钮 1 秒防抖

---

## RULE-FE-006: 报告 Markdown 安全渲染

- **触发**: 渲染 `report_markdown`
- **规则**: react-markdown 默认安全（不渲染 HTML），仅允许：
  - 标题 (h1-h6)、段落、加粗、斜体
  - 表格、有序/无序列表
  - 代码块、引用块
  - 链接（a 标签 href 过滤为 http/https 协议）
  - 不允许 raw HTML
- **引用**: react-markdown 安全机制

---

## RULE-FE-007: Toast 通知

- **触发**: 操作结果反馈
- **类型**:
  - success (绿色) — 操作成功
  - error (红色) — 操作失败
  - info (蓝色) — 状态提示
  - warning (黄色) — 警告
- **持续时间**: success/info 3 秒, error 5 秒, warning 需手动关闭
- **实现**: shadcn/ui Sonner 或自建 toast
