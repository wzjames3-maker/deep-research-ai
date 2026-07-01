# Task 26: 新建研究页面

## 对应 Spec
- specs/frontend/01-requirements.md REQ-FE-002
- specs/frontend/06-acceptance.md AC-FE-003

## 输入文件（Agent 需读取）
- specs/frontend/06-acceptance.md AC-FE-003
- frontend/src/api/research.ts（create 方法）
- frontend/src/types/index.ts（ResearchTemplate enum）

## 输出文件
- `frontend/src/pages/NewResearchPage.tsx`
- `frontend/src/components/Research/TemplateSelector.tsx`
- `frontend/src/components/Research/TopicInput.tsx`

## 前置任务
- Task 23（前端骨架 + API 封装）
- Task 18（POST /research/new 可用）

## 实现要求

### NewResearchPage (`/research/new`):
```
┌──────────────────────────────────────────┐
│  ← 返回仪表盘                              │
├──────────────────────────────────────────┤
│                                           │
│   输入研究主题                              │
│   ┌──────────────────────────────────┐    │
│   │ React 19 新特性...              │    │
│   └──────────────────────────────────┘    │
│   提示: 描述你的研究目标，越具体效果越好     │
│                                           │
│   选择研究模板                              │
│   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│   │ 技术  │ │ 竞品  │ │ 论文  │ │ 自定义 │   │
│   │ 调研  │ │ 分析  │ │ 综述  │ │      │   │
│   └──────┘ └──────┘ └──────┘ └──────┘   │
│                                           │
│   [ 开始研究 ]                             │
└──────────────────────────────────────────┘
```

### TopicInput:
- `textarea` 或 `input`, placeholder: "输入研究主题..."
- 字数统计: 限制 500 字符, 实时显示 `{count}/500`
- 前端校验: 非空, ≤500
- 受控组件（React state）

### TemplateSelector:
- 4 个可选卡片, 单选（目前选中的有蓝色边框/背景）
- 技术调研: `tech_research` — 图标: 齿轮/代码
- 竞品分析: `competitive_analysis` — 图标: 放大镜/对比
- 论文综述: `literature_review` — 图标: 书/论文
- 自定义: `custom` — 图标: 编辑/笔
- 使用 shadcn/ui RadioGroup 或自定义卡片组件

### 提交流程:
```
1. 前端校验: topic 非空 + template 已选
2. 按钮 Loading → 调用 research.create(topic, template)
3. 返回 researchId → navigate(`/research/${researchId}`)
4. 错误 → toast 展示
```

### 异常处理:
- 409 RESEARCH_IN_PROGRESS → toast "当前有一个进行中的研究", 提供跳转链接
- 500 PLAN_GENERATION_FAILED → toast "生成超时", 允许重试

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 18 POST /research/new 可用
- [ ] Task 23 前端路由配置正确

### AC 验收
- [ ] AC-FE-003: 输入主题 + 选模板 → loading → 跳转 `/research/{id}`, 渲染 PlanPanel

### 功能验收
- [ ] 4 个模板卡片可点击选择, 选中态高亮
- [ ] 主题为空时"开始研究"按钮禁用
- [ ] 主题 >500 字符时自动截断并提示
- [ ] 409 错误 → toast + 提供跳转到进行中研究的链接
- [ ] 500 错误 → toast + 按钮恢复可点击

### 代码质量
- [ ] 使用 shadcn/ui Textarea, Button, Card 组件
- [ ] 模板常量从 `types/` 定义引用（不硬编码字符串）
- [ ] 表单校验即时反馈（非仅提交时校验）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 27
