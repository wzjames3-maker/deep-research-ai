# 验收标准

## 来源
REQ-FE-001 ~ 011 + RULE-FE-001 ~ 007 + EC-FE-001 ~ 008

---

## AC-FE-001: 登录成功 (REQ-FE-001)

- **Given**: 已注册用户
- **When**: 在 `/login` 输入正确账号密码，点击"登录"
- **Then**:
  - [ ] 按钮变为 loading 状态
  - [ ] 成功后跳转到 `/dashboard`
  - [ ] localStorage 中存储 token 和 username
  - [ ] 页面头部显示用户名

---

## AC-FE-002: 注册表单校验 (RULE-FE-001)

- **Given**: 在 `/register` 页面
- **When**: 输入 `username="ab"`, `password="123"` 并提交
- **Then**:
  - [ ] 账号输入框下方显示"账号格式无效（3-50字符，仅字母数字下划线）"
  - [ ] 密码输入框下方显示"密码长度应为 8-64 字符"
  - [ ] 表单未提交（无网络请求）

---

## AC-FE-003: 新建研究 (REQ-FE-002)

- **Given**: 已登录, 在 `/research/new`
- **When**: 输入主题"React 19 新特性", 选择"技术调研", 点击"开始"
- **Then**:
  - [ ] 按钮变为 loading
- [ ] 成功后跳转到 `/research/{id}`，页面根据 status='draft' 渲染 PlanPanel

---

## AC-FE-004: 修改研究计划 (REQ-FE-003)

- **Given**: 在 `/research/{id}`，status='draft'，当前为第 2 轮
- **When**: 在聊天面板输入"去掉第 3 项"，点击发送
- **Then**:
  - [ ] 输入框清空，聊天记录显示用户消息
  - [ ] 显示"第 3/10 轮"
  - [ ] Loading 结束后计划卡片更新为新的 Sub-agent 列表

---

## AC-FE-005: 确认计划视图切换 (REQ-FE-003)

- **Given**: status='draft'，满意的研究计划
- **When**: 点击"确认计划"，API 返回 success
- **Then**:
  - [ ] URL 不变（仍在 `/research/{id}`）
  - [ ] 视图从 PlanPanel 切换到 ProgressDashboard
  - [ ] SSE 连接建立，Sub-agent 状态卡片显示

---

## AC-FE-006: SSE 进度显示 (REQ-FE-004)

- **Given**: 在 `/research/{id}`，status='running'，SSE 已连接
- **When**: Sub-agent 1 开始执行
- **Then**:
  - [ ] Sub-agent 1 卡片状态变为 running（蓝色旋转）
  - [ ] 显示当前搜索轮次 "1/2"
  - [ ] 显示当前搜索词

---

## AC-FE-007: Sub-agent 完成显示 (REQ-FE-004)

- **Given**: Sub-agent 1 完成
- **When**: 收到 `sub_agent_complete` 事件
- **Then**:
  - [ ] 卡片变绿色，状态显示 completed
  - [ ] 展示研究发现摘要（前 200 字符）
  - [ ] Token 消耗显示

---

## AC-FE-008: 报告查看 Tab 切换 (REQ-FE-005)

- **Given**: 在 `/research/{id}`，status='completed'，研究已完成
- **When**: 点击"Sub-agent 结果" Tab
- **Then**:
  - [ ] 展示各 Sub-agent 的详细发现（Markdown 渲染）
  - [ ] 来源 URL 以可点击链接展示
- **When**: 点击"研究汇总" Tab
- **Then**:
  - [ ] 展示完整汇总报告（Markdown 渲染，含表格/标题/列表）

---

## AC-FE-009: 引用溯源 (REQ-FE-006)

- **Given**: 报告中包含 `[1]` 引用标记
- **When**: 点击引用标记
- **Then**:
  - [ ] 新标签页打开原始来源 URL

---

## AC-FE-010: 报告复制 (REQ-FE-007)

- **Given**: 报告已显示
- **When**: 点击"复制 Markdown"按钮
- **Then**:
  - [ ] 剪贴板包含完整 Markdown 源码
  - [ ] 展示 toast "已复制到剪贴板"
- **When**: 点击"复制纯文本"按钮
- **Then**:
  - [ ] 剪贴板包含去掉 Markdown 语法后的纯文本

---

## AC-FE-011: 历史列表 (REQ-FE-008)

- **Given**: 已有 5 条研究记录
- **When**: 访问 `/research/history`
- **Then**:
  - [ ] 列表展示 5 条记录（按时间倒序）
  - [ ] 每条显示: 主题、模板、状态、Token 消耗、时间
  - [ ] 点击 → 跳转到对应报告页
  - [ ] 空列表 → 展示空状态插图和引导按钮

---

## AC-FE-012: 软删除 (REQ-FE-009)

- **Given**: 历史列表中 3 条记录
- **When**: 点击第 2 条的删除按钮 → 确认弹窗 → 确认
- **Then**:
  - [ ] 第 2 条从列表消失
  - [ ] 列表剩余 2 条
  - [ ] toast "已删除"

---

## AC-FE-013: Token 仪表盘 (REQ-FE-010)

- **Given**: 已登录, 在 `/dashboard`
- **When**: 页面加载完成
- **Then**:
  - [ ] 展示今日 Token 消耗、本周消耗、总研究次数、平均消耗

---

## AC-FE-014: 中断研究 (REQ-FE-011)

- **Given**: 在进度页，研究执行中
- **When**: 点击"停止"按钮 → 确认
- **Then**:
  - [ ] 进度卡片状态变为 cancelled
  - [ ] 若有部分结果 → 展示部分报告页
  - [ ] 若无结果 → 返回 `/dashboard` 并 toast "研究已终止"

---

## AC-FE-015: Token 过期 (RULE-FE-002)

- **Given**: 已登录, 但 token 已过期
- **When**: 访问 `/dashboard`
- **Then**:
  - [ ] API 返回 401
  - [ ] 自动跳转到 `/login`
  - [ ] toast "登录已过期，请重新登录"

---

## AC-FE-016: 登录失败 —— 账号锁定 (REQ-FE-001)

- **Given**: 账号已锁定
- **When**: 用正确密码登录
- **Then**:
  - [ ] HTTP 423
  - [ ] 展示 toast "账户已锁定，请 X 分钟后重试"
