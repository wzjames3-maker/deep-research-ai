# Task 30: 研究历史页面

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-008, 009
- specs/frontend/06-acceptance.md AC-FE-011, 012

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md（AC-FE-011, 012）
- frontend/src/api/research.ts（listHistory, delete）
- frontend/src/contexts/AuthContext.tsx

## 输出文件
- `frontend/src/pages/HistoryPage.tsx`
- `frontend/src/components/History/HistoryList.tsx`
- `frontend/src/components/History/HistoryItem.tsx`
- `frontend/src/components/History/DeleteConfirmDialog.tsx`

## 前置任务
- Task 22（GET /history + DELETE API 可用）
- Task 23（前端骨架）

## 实现要求

### HistoryPage 布局 (`/research/history`):
```
┌──────────────────────────────────────────────┐
│  ← 返回仪表盘                                  │
│                                              │
│  研究历史 (42)                                 │
├──────────────────────────────────────────────┤
│  搜索/筛选: [全部状态 ▾] [按时间逆序]           │
├──────────────────────────────────────────────┤
│  ┌────────────────────────────────────┐ [✕] │
│  │ React 19 新特性                     │      │
│  │ 技术调研 · 已完成 · 32K tokens      │      │
│  │ 2 小时前                            │      │
│  └────────────────────────────────────┘      │
│  ┌────────────────────────────────────┐ [✕] │
│  │ Vue vs React 对比                   │      │
│  │ 竞品分析 · 草稿 · —                │      │
│  │ 昨天                                │      │
│  └────────────────────────────────────┘      │
│  ...                                         │
│                                               │
│  [ 1 ]  [ 2 ]  [ 3 ]  ...  ← 分页            │
└──────────────────────────────────────────────┘
```

### HistoryItem 卡片:
- 左侧: 主题（标题）, 模板 badge + 状态 badge + token 消耗
- 右侧: 删除按钮（✕ 或 垃圾桶图标
- 点击卡片 → `navigate("/research/{id}")`
- 状态 badge 颜色:
  - completed: 绿色
  - draft: 灰色
  - running: 蓝色
  - failed: 红色
  - cancelled: 黄色

### 删除流程:
1. 点击删除按钮 → 弹出 DeleteConfirmDialog
2. Dialog: "确定删除「React 19 新特性」？删除后可在数据库中恢复。"
3. 确认 → `research.delete(researchId)` → toast "已删除"
4. 列表刷新, 该条目消失
5. 取消 → Dialog 关闭

### 分页:
- 默认 pageSize=20
- 底部页码导航（shadcn/ui Pagination 组件）
- 显示: "共 42 条, 当前第 1/3 页"

### 空状态:
- 无历史数据 → 插图 + "还没有研究记录" + "开始研究" 按钮

### 排序/筛选（可选 V1 简化）:
- 默认按 created_at DESC
- 可扩展: 按 status 筛选或按时间/Token 排序

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 22 GET /history 和 DELETE 接口可用
- [ ] 后端有测试数据供列表展示

### AC 验收
- [ ] AC-FE-011: 5 条记录 → 列表展示主题/模板/状态/Token/时间, 按时间倒序, 点击跳转报告
- [ ] AC-FE-012: 删除按钮 → 确认弹窗 → 成功 → toast "已删除", 列表剩 2 条

### 功能验收
- [ ] 分页功能正常（第 1 页 / 第 2 页 数据不重复）
- [ ] 空列表 → 空状态插图和引导按钮
- [ ] 删除后页面不刷新，列表动态更新
- [ ] 卡片点击跳转到正确的 /research/{id}

### 代码质量
- [ ] 使用 shadcn/ui Card, Badge, Button, Dialog, Pagination 组件
- [ ] 删除操作有 loading 状态（防重复点击）
- [ ] 状态 badge 颜色统一管理（enum → color mapping）
- [ ] 相对时间显示（"刚刚", "5 分钟前", "2 小时前", "昨天", "3 天前"）

### 通过判定
全部 ✅ → 任务 Done。Frontend 模块完成，进入 Phase 6（集成与交付）
