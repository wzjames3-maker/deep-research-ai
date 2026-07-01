# 接口契约

## 来源
PRD.md §3 UC-003 ~ UC-009 + REQ-RES-001 ~ 017

## 公共信息
- **前缀**: `/api/v1/research`
- **认证**: 所有接口需要 `Authorization: Bearer <token>`（auth 模块提供），SSE 端点除外（用 ticket 认证）
- **Content-Type**: `application/json`

---

## API-RES-001: 发起新研究

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/research/new` |

### Request Body
```json
{
  "topic": "string (required, 1-500 chars)",
  "template": "enum (required: tech_research | competitive_analysis | literature_review | custom)"
}
```

### Success Response (201)
```json
{
  "researchId": "uuid",
  "plan": {
    "subAgents": [
      {
        "id": "uuid",
        "name": "string",
        "goal": "string",
        "searchDirection": "string"
      }
    ]
  },
  "planRound": 1
}
```

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 400 | INVALID_TOPIC | 研究主题不能为空 | topic 为空或超过 500 字符 |
| 400 | INVALID_TEMPLATE | 无效的研究模板类型 | template 不在枚举中 |
| 409 | RESEARCH_IN_PROGRESS | 当前有一个进行中的研究 | RULE-RES-001 |
| 500 | PLAN_GENERATION_FAILED | 研究计划生成失败，请重试 | LLM 超时 30 秒 |

---

## API-RES-002: 修改研究计划

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/research/{researchId}/plan/revise` |
| **模式** | **同步**（阻塞等待 LLM 重新生成计划，耗时 5-15 秒） |

### Request Body
```json
{
  "feedback": "string (required, 1-1000 chars)"
}
```

### Success Response (200)
```json
{
  "plan": {
    "subAgents": [ /* 更新后的计划 */ ]
  },
  "planRound": 2
}
```

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 404 | NOT_FOUND | 研究记录不存在 | researchId 无效 |
| 400 | TOO_MANY_REVISIONS | 已达最大修改轮次（10轮） | RULE-RES-003 |
| 400 | INVALID_STATUS | 当前状态不允许修改计划 | status != 'draft' |
| 403 | FORBIDDEN | 无权操作该研究 | userId 不匹配 |
| 504 | PLAN_GENERATION_TIMEOUT | 计划生成超时（>30秒） | LLM 超时 |

### 前端使用说明
- 必须配置 **30 秒超时**（axios/HTTP client）
- 等待期间显示 **Loading 状态**（按钮禁用 + 骨架屏/Spinner）
- 超时后展示"计划生成超时，请重试"提示，允许用户重新提交

---

## API-RES-003: 确认研究计划

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/research/{researchId}/plan/confirm` |

### Request Body: 无

### Success Response (200)
```json
{
  "researchId": "uuid",
  "status": "running",
  "streamUrl": "/api/v1/research/{researchId}/stream"
}
```
> **前端使用方式**: 调用此接口后，先请求 `POST /api/v1/auth/ticket` 获取短效 ticket，再连接 `{streamUrl}?ticket={ticket}` 建立 SSE 连接。

### Error Responses
| HTTP | code | message | 触发条件 |
|---|---|---|---|
| 404 | NOT_FOUND | 研究记录不存在 | — |
| 403 | FORBIDDEN | 无权操作该研究 | userId 不匹配 |
| 400 | INVALID_STATUS | 当前状态不允许确认 | status != 'draft' |

---

## API-RES-004: SSE 研究进度流

| 属性 | 值 |
|---|---|
| **Method** | GET |
| **Path** | `/api/v1/research/{researchId}/stream?ticket=<ticket>` |
| **Content-Type** | `text/event-stream` |
| **Auth** | Ticket（通过 `?ticket=` 参数传入，由 API-AUTH-006 签发，30 秒有效） |

> **安全设计**: 浏览器 `EventSource` 不支持自定义 Header，因此通过 URL query param 传递短的 ticket 而非长期 JWT，避免 Token 泄露到 Nginx Access Log。

### SSE Event 类型

#### event: `plan_confirm` — 计划已确认
```json
{ "status": "confirmed", "researchId": "uuid" }
```

#### event: `sub_agent_start` — Sub-agent 开始执行
```json
{
  "subAgentId": "uuid",
  "name": "string",
  "goal": "string",
  "status": "running"
}
```

#### event: `sub_agent_round` — Sub-agent 进入新搜索轮次
```json
{
  "subAgentId": "uuid",
  "round": 1,
  "searchQuery": "string"
}
```

#### event: `sub_agent_complete` — Sub-agent 完成
```json
{
  "subAgentId": "uuid",
  "name": "string",
  "status": "completed",
  "roundsUsed": 2,
  "preview": "string (研究发现摘要, 前200字符)",
  "tokenUsed": 5000
}
```

#### event: `sub_agent_fail` — Sub-agent 失败
```json
{
  "subAgentId": "uuid",
  "name": "string",
  "status": "failed",
  "error": "string"
}
```

#### event: `report_complete` — 汇总完成
```json
{
  "status": "completed",
  "reportMarkdown": "string",
  "totalTokens": 32000
}
```

#### event: `error` — 顶层错误
```json
{
  "status": "failed",
  "error": "string (如：所有Sub-agent均失败)"
}
```

#### event: `heartbeat` — 连接保活（每 15 秒）
```json
{ "type": "heartbeat" }
```

---

## API-RES-005: 获取研究详情（任意阶段）

| 属性 | 值 |
|---|---|
| **Method** | GET |
| **Path** | `/api/v1/research/{researchId}` |

### Success Response (200)
```json
{
  "researchId": "uuid",
  "topic": "string",
  "template": "string",
  "status": "draft",
  "plan": { "subAgents": [ /* ... */ ] },
  "totalTokens": 0,
  "planRound": 3,
  "subAgentResults": [],
  "createdAt": "ISO8601",
  "startedAt": null,
  "completedAt": null
}
```
> 返回数据随 status 变化：status='draft' 时仅含 plan；status='running' 时含部分 subAgentResults；status='completed' 时含完整报告。

### 用途
- 前端页面刷新后恢复当前研究状态（Hydration）
- 工作台 `/research/{id}` 加载时获取最新研究状态，根据 status 驱动视图切换

### Error Responses
| HTTP | code | trigger |
|---|---|---|
| 404 | NOT_FOUND | 不存在或已删除 |
| 403 | FORBIDDEN | 无权访问该研究（userId 不匹配） |

---

## API-RES-006: 获取研究报告

| 属性 | 值 |
|---|---|
| **Method** | GET |
| **Path** | `/api/v1/research/{researchId}/report` |

### Success Response (200)
```json
{
  "researchId": "uuid",
  "topic": "string",
  "template": "string",
  "status": "completed | cancelled",
  "plan": { "subAgents": [ /* ... */ ] },
  "reportMarkdown": "string",
  "subAgentResults": [
    {
      "name": "string",
      "goal": "string",
      "status": "completed | failed | cancelled",
      "findings": "string (Markdown)",
      "visitedUrls": ["url1", "url2"],
      "tokenUsed": 5000
    }
  ],
  "totalTokens": 32000,
  "createdAt": "ISO8601",
  "completedAt": "ISO8601"
}
```
> `status` 可能为 `completed`（全部/部分成功）或 `cancelled`（中断后有部分报告）。

### Error Responses
| HTTP | code | trigger |
|---|---|---|
| 404 | NOT_FOUND | 不存在或已删除 |
| 400 | REPORT_NOT_READY | status 为 'draft' / 'running' / 'failed'（无报告） |

> **注意**: `cancelled` 状态的研究如果有部分报告（基于已完成的 Sub-agent 生成），允许通过此接口查看。若 `reportMarkdown` 为 null（如 10 秒内中断且无结果），返回 400 REPORT_NOT_READY。

---

## API-RES-007: 研究历史列表

| 属性 | 值 |
|---|---|
| **Method** | GET |
| **Path** | `/api/v1/research/history` |
| **Query** | `?page=1&pageSize=20` |

### Success Response (200)
```json
{
  "items": [
    {
      "researchId": "uuid",
      "topic": "string",
      "template": "string",
      "status": "completed",
      "totalTokens": 32000,
      "createdAt": "ISO8601"
    }
  ],
  "total": 42,
  "page": 1,
  "pageSize": 20
}
```
> 按 `created_at DESC` 排序，默认过滤 `deleted_at IS NULL`

### Error Responses
| HTTP | code | trigger |
|---|---|---|
| 401 | TOKEN_INVALID | 未认证或 Token 过期 |

---

## API-RES-008: 中断研究

| 属性 | 值 |
|---|---|
| **Method** | POST |
| **Path** | `/api/v1/research/{researchId}/cancel` |

### Success Response (200)
```json
{
  "researchId": "uuid",
  "status": "cancelled"
}
```

### 业务逻辑
- 若已有部分 Sub-agent 完成 → 保留其结果, status='cancelled'，基于已有结果生成部分报告
- 若 10 秒内且无任何 Sub-agent 返回有效结果 → 保留记录但不生成报告
- 若所有 Sub-agent 均 pending → 直接标记 cancelled

### Error Responses
| HTTP | code | trigger |
|---|---|---|
| 404 | NOT_FOUND | 研究记录不存在或已删除 |
| 403 | FORBIDDEN | userId 不匹配 |
| 400 | INVALID_STATUS | status 非 'running'（如已完成/已取消） |

---

## API-RES-009: 软删除研究

| 属性 | 值 |
|---|---|
| **Method** | DELETE |
| **Path** | `/api/v1/research/{researchId}` |

### Success Response (200)
```json
{ "deleted": true }
```

### 业务逻辑
- 设置 `deleted_at = NOW()`，不执行物理 DELETE
- 前端不再展示该记录

### Error Responses
| HTTP | code | trigger |
|---|---|---|
| 404 | NOT_FOUND | 不存在或已被删除 |
| 403 | FORBIDDEN | userId 不匹配 |

---

## API-RES-010: Token 消耗统计

| 属性 | 值 |
|---|---|
| **Method** | GET |
| **Path** | `/api/v1/research/stats/tokens` |

### Success Response (200)
```json
{
  "todayTokens": 95000,
  "weekTokens": 450000,
  "totalResearches": 15,
  "avgTokensPerResearch": 30000
}
```

### Error Responses
| HTTP | code | trigger |
|---|---|---|
| 401 | TOKEN_INVALID | 未认证或 Token 过期 |
