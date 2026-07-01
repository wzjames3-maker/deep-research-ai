# Task 20: 研究中断接口

## 对应 Spec
- specs/research/03-api-contract.md API-RES-008 (POST /cancel)
- specs/research/06-acceptance.md AC-RES-012, 013
- specs/research/04-business-rules.md RULE-RES-009（取消逻辑）

## 输入文件（Agent 需读取）
- specs/research/03-api-contract.md API-RES-008
- specs/research/04-business-rules.md RULE-RES-009
- src/services/exec_engine.py（执行引擎，需添加取消支持）
- src/services/sse_manager.py（SSE 管理器）
- src/repos/research_repo.py / sub_agent_result_repo.py
- src/middleware/auth.py

## 输出文件
- `src/api/research/router.py`（追加 POST /cancel）
- `src/services/exec_engine.py`（追加 `cancel_execution` 方法）

## 前置任务
- Task 19（执行引擎可用）

## 实现要求

### POST `/api/v1/research/{id}/cancel` (API-RES-008):
```
1. Auth
2. 查找 Research → 404 / 403
3. status != 'running' → 400 INVALID_STATUS
4. 设置全局取消标志 (e.g., cancel_signals[research_id] = True)
5. 执行引擎检测到取消标志后：
   a. 终止所有进行中的 Sub-agent
   b. 已完成的 Sub-agent 结果保留 → 运行汇总 Agent 生成部分报告
   c. 全部 pending → 直接标记 cancelled
6. 返回 200: { researchId, status: "cancelled" }
```

### 取消标志机制:
```python
# src/services/exec_engine.py
cancel_signals: dict[UUID, asyncio.Event] = {}

async def cancel_execution(research_id: UUID):
    cancel_signals[research_id].set()

async def check_cancelled(research_id: UUID) -> bool:
    return cancel_signals.get(research_id, asyncio.Event()).is_set()
```

### 3 种取消场景:
| 场景 | 条件 | 行为 |
|---|---|---|
| 立即取消（无结果） | 10 秒内 + 无有效 Sub-agent 结果 | status='cancelled', report=NULL, SSE 不生成报告 |
| 部分结果取消 | 部分 Sub-agent 已完成 | 基于已完成结果调汇总 Agent → 部分报告 |
| 全部待执行取消 | 无 started Sub-agent | status='cancelled', 不调汇总 Agent |

### SSE 通知:
- 取消时推送事件通知前端: `{"status": "cancelled", "subAgentResults": [...]}`

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 19 执行引擎中有运行中的研究可取消
- [ ] SSE 连接处于活跃状态

### AC 验收
- [ ] AC-RES-012: 10 秒内取消 + 无结果 → status='cancelled', report=NULL
- [ ] AC-RES-013: 部分完成 + 取消 → 部分报告, 剩余 Sub-agent status='cancelled'

### 功能验收
- [ ] POST /cancel → running 状态变为 cancelled
- [ ] 取消后 SSE 推送适当地关闭或推送最终状态
- [ ] 重复取消返回 400 INVALID_STATUS

### 代码质量
- [ ] 取消标志清理（避免内存泄漏）
- [ ] 并发安全（asyncio.Event 线程安全）
- [ ] 中断后已完成的 Sub-agent 数据保留完整

### 通过判定
全部 ✅ → 任务 Done，进入 Task 21
