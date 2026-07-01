# Task 29: ReportView 视图（Tab + 复制）

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-005, 006, 007
- specs/frontend/06-acceptance.md AC-FE-008, 009, 010
- specs/research/06-acceptance.md AC-RES-017, 018

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md（AC-FE-008, 009, 010）
- frontend/src/api/research.ts（getReport）
- frontend/src/pages/WorkbenchPage.tsx

## 输出文件
- `frontend/src/components/Research/ReportView.tsx`
- `frontend/src/components/Research/ReportTabs.tsx`
- `frontend/src/components/Research/MarkdownRenderer.tsx`

## 前置任务
- Task 21（GET /report API 可用）
- Task 27（WorkbenchPage 可切换到 ReportView）
- Task 23（react-markdown 已安装）

## 实现要求

### ReportView 布局 (`/research/{id}`, status='completed'):
```
┌──────────────────────────────────────────────┐
│  研究报告: React 19 新特性                     │
│  模板: 技术调研 · 总耗时: 5:30 · 32K tokens    │
├──────────────────────────────────────────────┤
│  [ 研究计划 ]  [ Sub-agent 结果 ]  [ 研究汇总 ] │  ← Tabs
├──────────────────────────────────────────────┤
│                                               │
│  (Tab 内容区域 — Markdown 渲染)                │
│                                               │
│  [ 复制 Markdown ]  [ 复制纯文本 ]  [ 重新研究 ]│
└──────────────────────────────────────────────┘
```

### 3 个 Tab:

#### Tab 1: 研究计划
- 展示原始确认的 Sub-agent 计划
- 显示: name, goal, searchDirection（只读列表）

#### Tab 2: Sub-agent 结果
- 每个 Sub-agent 的结果卡片:
  - name, goal
  - findings (Markdown 渲染, react-markdown)
  - 来源 URLs — 可点击跳转（新标签页打开）
  - token 消耗
- `findings` 中的引用标记 `[1]` / `[n]` → 可点击跳转对应的 visitedUrls

#### Tab 3: 研究汇总
- 完整 Markdown 报告（react-markdown + remark-gfm 渲染）
- 支持: 表格、标题层级、列表、代码块、引用
- 引用溯源: Markdown 链接可点击（`target="_blank"`）

### MarkdownRenderer:
```tsx
function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
            {children}
          </a>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto">
            <table className="border-collapse border">{children}</table>
          </div>
        ),
        // ... 其他组件定制
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

### 复制功能:
- "复制 Markdown": `navigator.clipboard.writeText(reportMarkdown)` → toast "已复制"
- "复制纯文本": 用 DOM 解析去除 Markdown 语法 → clipboard → toast
- 使用 shadcn/ui Button + Copy icon

### 重新研究:
- "重新研究" 按钮 → `navigate("/research/new")` + 预填 topic（通过 URL param 或 state）

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 21 GET /report 返回完整数据（reportMarkdown + subAgentResults）
- [ ] react-markdown 和 remark-gfm 已安装

### AC 验收
- [ ] AC-FE-008: 3 Tab 切换, "Sub-agent 结果" → findings Markdown + 来源链接, "研究汇总" → 完整报告
- [ ] AC-FE-009: 引用标记可点击 → 新标签页打开原始来源
- [ ] AC-FE-010: "复制 Markdown" → 剪贴板含完整源码, toast; "复制纯文本" → 剪贴板含纯文本

### 功能验收
- [ ] Tab 切换不重新请求 API（数据已在 WorkbenchPage hydrate 时获取）
- [ ] 表格渲染正确（边框、对齐）
- [ ] 长内容可滚动（overflow-y-auto）
- [ ] "重新研究" 按钮 → 跳转 /research/new, topic 已预填

### 代码质量
- [ ] react-markdown 不渲染 HTML（防止 XSS, `allowedElements` 白名单模式）
- [ ] 复制失败时 toast 错误提示（如浏览器不支持 Clipboard API）
- [ ] 代码块有语法高亮（可选, 使用 `react-syntax-highlighter`）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 30
