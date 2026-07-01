# Task 16: MCP 搜索客户端

## 对应 Spec
- specs/research/04-business-rules.md:
  - RULE-RES-005（搜索循环 ≤ 2 轮）
  - RULE-RES-006（URL 去重但允许重复内容）
- specs/research/08-dependencies.md（Brave Search MCP Server）
- docs/research-report.md §模块2 (Brave Search MCP)

## 输入文件（Agent 需读取）
- specs/research/08-dependencies.md
- specs/research/04-business-rules.md（RULE-RES-005, 006）
- docs/research-report.md §模块2
- docs/tech-decision.md §决策4 (MCP 协议)
- src/config.py（BRAVE_API_KEY）

## 输出文件
- `src/services/mcp_client.py`（MCP 客户端封装）

## 前置任务
- Task 01（config.py 中 BRAVE_API_KEY 可用）
- Task 00（Brave Search MCP 容器已在 docker-compose 中定义）

## 实现要求

### 1. MCP 客户端封装 (`src/services/mcp_client.py`):

使用 `mcp-sdk`（Python MCP SDK v1.x）或直接 HTTP 调用 Brave Search MCP Server。

```python
class MCPSearchClient:
    def __init__(self, mcp_endpoint: str, api_key: str):
        ...
    
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """执行一次搜索，返回 (url, title, snippet) 列表"""
        ...
    
    async def search_multi_round(self, directions: list[str], existing_urls: set[str], max_rounds: int = 2) -> list[list[SearchResult]]:
        """多轮搜索: 每轮换方向，URL 去重"""
        ...
```

### 2. SearchResult 数据模型:
```python
@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
```

### 3. URL 去重逻辑:
- 维护跨轮次的 `visited_urls: set[str]`
- 每轮搜索结果中，已访问过的 URL 过滤掉
- 新 URL 追加到 `visited_urls`
- **注意**: 仅 URL 去重，不做语义去重

### 4. 降级策略:
- Brave Search MCP 不可用 → 自动尝试 Tavily MCP（通过配置 `TAVILY_API_KEY`）
- 两个都不可用 → 抛出异常，Sub-agent 标记为 failed

### 5. 日志:
- 每次搜索记录: search_query, results_count, new_urls_count, duration_ms

## 验收检查点（Checkpoint）

### 前置确认
- [ ] Task 00 Brave Search MCP 容器已在 docker-compose 中定义并可访问
- [ ] BRAVE_API_KEY 已在 .env 中配置

### 功能验收
- [ ] `search("React 19 new features", max_results=5)` → 返回 5 条或更少的结果
- [ ] 每条结果含 url, title, snippet
- [ ] 搜索结果 url 列表可用于去重检查
- [ ] `search_multi_round()` 第 2 轮自动排除第 1 轮已访问的 URL

### AC 验收
- [ ] AC-RES-008: 第 1 轮 [A,B,C], 第 2 轮 [B,D,E] → 仅 D, E 被输入 LLM

### 代码质量
- [ ] 搜索调用有超时设置（10 秒）
- [ ] MCP 连接错误有重试机制（最多 2 次）
- [ ] 降级到 Tavily 的逻辑可配置开关（`SEARCH_BACKUP=tavily` / `none`）
- [ ] visited_urls 保存在 SubAgentResult 的 JSONB 字段中

### 通过判定
全部 ✅ → 任务 Done。Research 基础设施完成，进入 Phase 4 (Research 业务逻辑)
