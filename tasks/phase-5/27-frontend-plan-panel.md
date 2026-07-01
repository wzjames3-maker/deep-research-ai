# Task 27: PlanPanel 视图（计划审核 + 修改）

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-003（工作台, status='draft'/'confirmed'）
- specs/frontend/06-acceptance.md AC-FE-004, 005

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md AC-FE-004, 005
- frontend/src/api/research.ts（revise, confirm, get）
- frontend/src/pages/WorkbenchPage.tsx（主工作台页面容器）

## 输出文件
- `frontend/src/pages/WorkbenchPage.tsx`（状态驱动页面容器）
- `frontend/src/components/Research/PlanPanel.tsx`（计划面板）
- `frontend/src/components/Research/PlanCard.tsx`（单个 Sub-agent 卡片）
- `frontend/src/components/Research/ChatPanel.tsx`（多轮对话面板）
- `frontend/src/components/Research/ChatBubble.tsx`（聊天气泡）

## 前置任务
- Task 23（前端骨架 + WorkbenchPage 占位）
- Task 26（新建研究后跳转到此页面）
- Task 18（/revise + /confirm API 可用）

## 实现要求

### WorkbenchPage 容器 (`/research/{id}`):
```tsx
function WorkbenchPage() {
  const { id } = useParams();
  const [research, setResearch] = useState<Research | null>(null);
  
  // Hydration: 加载时调用 GET /api/v1/research/{id}
  useEffect(() => {
    researchApi.get(id).then(setResearch);
  }, [id]);
  
  // 状态驱动视图切换
  if (!research) return <LoadingSkeleton />;
  
  if (research.status === 'draft' || research.status === 'confirmed') {
    return <PlanPanel research={research} onUpdate={setResearch} />;
  }
  if (research.status === 'running') {
    return <ProgressDashboard research={research} onUpdate={setResearch} />;
  }
  if (research.status === 'completed') {
    return <ReportView research={research} onUpdate={setResearch} />;
  }
  // failed / cancelled
  return <ErrorView research={research} />;
}
```

### PlanPanel 布局:
```
┌──────────────────────────────────────────────┐
│  研究主题: React 19 新特性                      │
│  模板: 技术调研 · 状态: 草稿 · 第 2/10 轮       │
├──────────────────────────────────────────────┤
│  Sub-agent 计划:                               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │ Agent 1 │ │ Agent 2 │ │ Agent 3 │ ...    │
│  │ 目标:.. │ │ 目标:.. │ │ 目标:.. │        │
│  │ 方向:.. │ │ 方向:.. │ │ 方向:.. │        │
│  └─────────┘ └─────────┘ └─────────┘        │
│                                               │
│  [ 确认计划 ]                                  │
├──────────────────────────────────────────────┤
│  修改建议 (聊天面板):                           │
│  ┌───────────────────────────────────────┐   │
│  │ 用户: 增加一个对比 Vue 的子任务         │   │
│  │ AI: 已更新计划，新增 Agent 4...        │   │
│  │ 用户: 去掉第 3 项                      │   │
│  │ AI: 好的，已调整为 3 个 Sub-agent      │   │
│  └───────────────────────────────────────┘   │
│  ┌───────────────────────────────────────┐   │
│  │ 输入修改建议...                  [发送] │   │
│  └───────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

### PlanCard (单个 Sub-agent):
- 显示: name (标题), goal (描述), searchDirection (搜索方向)
- 视觉: shadcn/ui Card, 左侧彩色条纹标识
- 数量: 3-5 张卡片排列

### ChatPanel:
- 聊天记录: 用户消息 + AI 响应气泡
- 输入框 + 发送按钮
- 发送后 → Loading → AI 回复显现
- 轮次显示: "第 3/10 轮"
- 最大 10 轮 → 达到后禁用输入 + 提示 "已达到最大修改轮次"

### 确认计划:
- "确认计划" 按钮
- 点击 → `research.confirm(id)` → 更新 research.status='running'
- 父组件 WorkbenchPage 检测 status 变化 → 切换到 ProgressDashboard

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 18 /revise 和 /confirm API 可用
- [ ] Task 23 WorkbenchPage 容器已创建

### AC 验收
- [ ] AC-FE-004: 输入反馈 → loading → 计划卡片更新, "第 3/10 轮"
- [ ] AC-FE-005: 确认计划 → URL 不变, 视图丝滑切换到 ProgressDashboard

### 功能验收
- [ ] 页面刷新（Hydration）→ GET /{id} → 恢复 draft 状态和计划
- [ ] /revise 超时 → toast "生成超时, 请重试", 输入框恢复可用
- [ ] 第 10 轮 → 输入框禁用, 提示 "已达到最大修改轮次, 请确认计划"
- [ ] status='confirmed' → PlanPanel 不变, 等待 SSE 推送 running

### 代码质量
- [ ] ChatPanel 使用虚拟滚动或限制消息数量（避免 DOM 溢出）
- [ ] 发送按钮在 loading 时禁用（防止重复提交）
- [ ] PlanCard 数据从 research.plan.subAgents 动态渲染

### 通过判定
全部 ✅ → 任务 Done，进入 Task 28
