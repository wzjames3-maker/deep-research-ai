# Task 28: ProgressDashboard 视图（SSE 消费）

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-004（实时进度） + REQ-FE-011（中断研究）
- specs/frontend/06-acceptance.md AC-FE-006, 007, 014

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md（AC-FE-006, 007, 014）
- frontend/src/api/research.ts（cancel, ticket）
- frontend/src/hooks/useSSE.ts（SSE 连接 hook, Task 23 产出）
- frontend/src/pages/WorkbenchPage.tsx（状态容器）

## 输出文件
- `frontend/src/components/Research/ProgressDashboard.tsx`
- `frontend/src/components/Research/AgentStatusCard.tsx`
- `frontend/src/hooks/useSSE.ts`（增强: 事件回调类型定义）

## 前置任务
- Task 23（useSSE hook 骨架）
- Task 19（SSE 流端点可用）
- Task 27（WorkbenchPage 可切换到 ProgressDashboard）

## 实现要求

### ProgressDashboard 布局 (`/research/{id}`, status='running'):
```
┌─────────────────────────────────────────────────┐
│  正在研究: React 19 新特性                        │
│  已完成: 1/3  ·  总耗时: 2:35                     │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │      │
│  │ 新特性分析 │  │ 性能对比  │  │ 迁移指南  │      │
│  │ ✅ 已完成  │  │ 🔄 搜索中 │  │ ⏳ 等待中  │      │
│  │ 2/2 轮    │  │ 1/2 轮    │  │ —        │      │
│  │ 5.2K tokens│ │ 搜索: RSC │  │          │      │
│  │ 前200字... │  │          │  │          │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  [ ⏹ 停止研究 ]                                   │
└─────────────────────────────────────────────────┘
```

### AgentStatusCard 状态:
| 状态 | 外观 | 行为 |
|---|---|---|
| pending | 灰色, 时钟图标 | 等待开始 |
| running | 蓝色边框, 旋转 spinner | 显示当前搜索词 + 轮次 |
| completed | 绿色边框 + 对勾 | 显示发现摘要 + token |
| failed | 红色边框 + 叉号 | 显示错误原因 |
| cancelled | 灰色, 删除线 | 已被终止 |

### SSE 事件处理:
```
useSSE(researchId):

sub_agent_start:
  → 卡片 pending → running（蓝色旋转）

sub_agent_round:
  → 更新卡片: round="1/2", searchQuery="当前搜索词"

sub_agent_complete:
  → 卡片变绿, 显示 preview (前 200 字), tokenUsed

sub_agent_fail:
  → 卡片变红, 显示 error message

report_complete:
  → 更新 research.status='completed'
  → WorkbenchPage 检测变化 → 切换到 ReportView

error:
  → 全部失败 → 显示全局错误状态

heartbeat:
  → (内部, 仅用于断连检测)

连接断开:
  → 自动重连: 重新获取 ticket + 重新建立 EventSource
  → 重连后通过 GET /{id} 恢复当前进度
```

### 停止按钮:
- 按钮: "停止研究" (shadcn/ui Button, variant="destructive")
- 点击 → 确认弹窗 (shadcn/ui Dialog)："确定停止当前研究？已完成的结果将保留"
- 确认 → `research.cancel(id)` → 更新状态
- 停止后 SSE 自动断开

### 计时器:
- 显示研究开始到当前的耗时
- 使用 `useEffect` + `setInterval`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 19 SSE 流可用
- [ ] Task 23 useSSE hook 骨架存在
- [ ] Task 27 WorkbenchPage 可传递 status change

### AC 验收
- [ ] AC-FE-006: Sub-agent 开始 → 卡片蓝色旋转 + "1/2" + 搜索词
- [ ] AC-FE-007: Sub-agent 完成 → 绿色对勾 + 摘要 + token
- [ ] AC-FE-014: 停止按钮 → 确认 → 卡片 cancelled / 部分报告

### 功能验收
- [ ] SSE 断连 → 自动重连（重新获取 ticket）
- [ ] 刷新页面 → GET /{id} → 恢复 running 状态 + 已完成的卡片
- [ ] 所有 Sub-agent 完成 → 自动切换到 ReportView
- [ ] 部分 Sub-agent 失败 → 其余继续, 最后仍能完成

### 代码质量
- [ ] EventSource close() 在组件卸载时调用（防止内存泄漏）
- [ ] 重连逻辑有退避策略（1s, 2s, 4s...）
- [ ] AgentStatusCard 使用 shadcn/ui Card + Badge
- [ ] 计时器格式: "MM:SS"

### 通过判定
全部 ✅ → 任务 Done，进入 Task 29
