# Task 25: 仪表盘页面

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-010
- specs/frontend/06-acceptance.md AC-FE-013

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md AC-FE-013
- frontend/src/api/research.ts（getTokenStats）
- frontend/src/api/auth.ts（me / hydrate）
- frontend/src/contexts/AuthContext.tsx

## 输出文件
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/Dashboard/` 目录:
  - `TokenStatsCards.tsx`（Token 消耗卡片）
  - `QuickActions.tsx`（新建研究 + 查看历史按钮）
  - `RecentResearches.tsx`（最近 5 条研究）

## 前置任务
- Task 23（前端骨架）
- Task 13（/auth/me 可用）
- Task 22（/research/stats/tokens 可用）

## 实现要求

### DashboardPage 布局:
```
┌─────────────────────────────────────────────┐
│  HeaderBar: 用户名 + 退出                     │
├─────────────────────────────────────────────┤
│  [今日Token] [本周Token] [总研究数] [平均消耗]  │  ← TokenStatsCards
├─────────────────────────────────────────────┤
│  [ 新建研究 ]  [ 查看全部历史 ]                 │  ← QuickActions
├─────────────────────────────────────────────┤
│  最近研究:                                    │  ← RecentResearches
│  - React 19 新特性 (完成) 32K tokens 2h前     │
│  - Vue vs React 对比 (草稿) — 昨天           │
│  - ...                                       │
└─────────────────────────────────────────────┘
```

### TokenStatsCards:
- 调用 `/api/v1/research/stats/tokens` 获取数据
- 4 张卡片: `今日消耗`, `本周消耗`, `总研究次数`, `平均每次`
- 使用 shadcn/ui Card 组件
- Loading 状态: Skeleton 闪烁效果

### QuickActions:
- "新建研究" Button → `navigate("/research/new")`
- "查看全部历史" Button → `navigate("/research/history")`

### RecentResearches:
- 调用 `/api/v1/research/history?page=1&pageSize=5` 获取最近数据
- 每条显示: topic, status badge, totalTokens, createdAt (相对时间)
- 点击 → `/research/{id}`
- 空列表 → 引导文字 + 新建按钮

### HeaderBar:
- 显示登录用户名（从 AuthContext）
- 退出按钮 → `logout()` → 清除 token → `/login`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 22 Token stats API 返回数据
- [ ] Task 13 /auth/me 可用

### AC 验收
- [ ] AC-FE-013: 仪表盘展示今日 Token、本周 Token、总研究数、平均消耗
- [ ] 4 个指标卡片数据正确（与后端 API 返回一致）

### 功能验收
- [ ] 页面加载时 Hydration: GET /auth/me → username 显示在 Header
- [ ] 退出按钮清除 localStorage token → 跳转 /login
- [ ] 点击"新建研究" → 跳转 /research/new
- [ ] 最近研究列表点击 → 跳转 /research/{id}

### 代码质量
- [ ] 使用 shadcn/ui Card, Skeleton, Button, Badge 组件
- [ ] 响应式: 4 卡片一行（桌面），2 卡片一行（窄屏）
- [ ] 数字格式化: Token 消耗使用 K（千）/ M（百万）单位

### 通过判定
全部 ✅ → 任务 Done，进入 Task 26
