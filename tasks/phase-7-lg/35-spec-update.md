# Task 35: 验证 Spec 文件更新（已完成）

## 对应 Spec
- specs/research/00-overview.md ~ 08-dependencies.md（全部）

## 说明

> **此任务已在 Phase 4 由人工 + AI 完成执行。**
> Spec 文件已按 LangGraph 迁移方案更新。此任务为**验证任务**，确认所有 spec 文件已正确更新，无遗漏。

## 输入文件（Agent 需读取）
- specs/research/00-overview.md
- specs/research/03-api-contract.md
- specs/research/04-business-rules.md
- specs/research/05-edge-cases.md
- specs/research/06-acceptance.md
- specs/research/07-tech-constraints.md
- specs/research/08-dependencies.md
- docs/tech-decision.md（决策4）

## 输出文件
- 无（验证任务，如发现问题则修正对应 spec 文件）

## 前置任务
- 无（可与 Task 33、34 并行）

## 验证清单

### tech-decision.md
- [ ] 决策4 已移除 "降级备选" 语言
- [ ] 决策4 确认 LangGraph 为唯一方案
- [ ] 架构总图已更新（FastAPI 框为 LangGraph 而非 asyncio）

### 00-overview.md
- [ ] 技术栈表：编排框架列为 `LangGraph StateGraph`
- [ ] 决策分类表：LangGraph 从 "首选" 改为 "已确认"
- [ ] 迭代记录存在

### 01-requirements.md
- [ ] **未改动**（业务需求不随技术方案变化）

### 02-data-model.md
- [ ] **未改动**（无新表、无新字段）

### 03-api-contract.md
- [ ] API-RES-001 有 V1.1.0 实现变更注释
- [ ] API-RES-002 有 V1.1.0 实现变更注释
- [ ] API-RES-003 有 V1.1.0 实现变更注释
- [ ] API-RES-008 有 V1.1.0 实现变更注释
- [ ] 请求/响应格式未变

### 04-business-rules.md
- [ ] RULE-RES-004: Send API 替代 asyncio.gather + State Reducer 说明
- [ ] RULE-RES-005: conditional edge 替代 for 循环
- [ ] RULE-RES-009: Hybrid 取消机制（update_state + asyncio.Event）
- [ ] RULE-RES-010: 新增 checkpoint 清理

### 05-edge-cases.md
- [ ] EC-RES-013: checkpoint 恢复
- [ ] EC-RES-014: 废弃草稿清理

### 06-acceptance.md
- [ ] AC-RES-025: checkpoint 恢复
- [ ] AC-RES-026: interrupt → resume 流程
- [ ] AC-RES-027: hybrid 取消机制

### 07-tech-constraints.md
- [ ] 移除 asyncio 降级段
- [ ] StateGraph 结构图完整
- [ ] ResearchState 定义含 `_action` 字段 + `sub_agent_results` reducer
- [ ] SubAgentState 定义存在
- [ ] Send API 说明
- [ ] interrupt() 恢复 API 正确（Command(resume=...) vs ainvoke(None)）
- [ ] PostgresSaver（AsyncPostgresSaver）说明
- [ ] RunnableConfig 注入说明
- [ ] Hybrid 取消机制说明
- [ ] Checkpoint 清理说明
- [ ] 禁止使用列表更新

### 08-dependencies.md
- [ ] langgraph + langgraph-checkpoint-postgres 依赖
- [ ] Graph Node 函数签名
- [ ] API 层调用接口
- [ ] checkpoint 表列入数据库对象

## 验收检查点（Checkpoint）

### 通过判定
全部 ✅ → 任务 Done，进入 Task 36
