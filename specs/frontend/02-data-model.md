# 数据模型（前端状态）

> 前端无独立数据库，此文件定义前端状态结构和 API 响应 TypeScript 类型。

## 来源
specs/auth/03-api-contract.md + specs/research/03-api-contract.md

---

## 前端状态类型

### AuthState
```typescript
type AuthState = {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  expiresIn: number;
};

type User = {
  userId: string;
  username: string;
};
```

### ResearchState
```typescript
type ResearchState = {
  currentResearch: Research | null;
  history: ResearchSummary[];
  tokenStats: TokenStats | null;
};

type Research = {
  researchId: string;
  topic: string;
  template: ResearchTemplate;
  status: ResearchStatus;
  plan: ResearchPlan | null;
  planRound: number;
  reportMarkdown: string | null;
  subAgentResults: SubAgentResult[];
  totalTokens: number;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
};

type ResearchSummary = {
  researchId: string;
  topic: string;
  template: string;
  status: string;
  totalTokens: number;
  createdAt: string;
};

type TokenStats = {
  todayTokens: number;
  weekTokens: number;
  totalResearches: number;
  avgTokensPerResearch: number;
};
```

### Sub-Agent 类型
```typescript
type SubAgent = {
  id: string;
  name: string;
  goal: string;
  searchDirection: string;
};

type ResearchPlan = {
  subAgents: SubAgent[];
};

type SubAgentResult = {
  name: string;
  goal: string;
  status: SubAgentStatus;
  findings: string;
  visitedUrls: string[];
  tokenUsed: number;
};
```

### SSE Event Types
```typescript
// 注: SSE 事件中 Sub-agent ID 字段名为 subAgentId（与 plan 中的 id 不同，待后端统一）
type SSEEvent =
  | { type: 'plan_confirm'; data: { status: 'confirmed'; researchId: string } }
  | { type: 'sub_agent_start'; data: { subAgentId: string; name: string; goal: string; status: 'running' } }
  | { type: 'sub_agent_round'; data: { subAgentId: string; round: number; searchQuery: string } }
  | { type: 'sub_agent_complete'; data: { subAgentId: string; name: string; status: 'completed'; roundsUsed: number; preview: string; tokenUsed: number } }
  | { type: 'sub_agent_fail'; data: { subAgentId: string; name: string; status: 'failed'; error: string } }
  | { type: 'report_complete'; data: { status: 'completed'; reportMarkdown: string; totalTokens: number } }
  | { type: 'error'; data: { status: 'failed'; error: string } }
  | { type: 'heartbeat'; data: { type: 'heartbeat' } };
```

### 枚举类型
```typescript
type ResearchTemplate = 'tech_research' | 'competitive_analysis' | 'literature_review' | 'custom';
type ResearchStatus = 'draft' | 'confirmed' | 'running' | 'completed' | 'failed' | 'cancelled';
type SubAgentStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
```

### 模板选项（中文显示）
```typescript
const TEMPLATE_OPTIONS = [
  { value: 'tech_research', label: '技术调研', description: '技术原理、生态、竞品、应用、趋势' },
  { value: 'competitive_analysis', label: '竞品分析', description: '市场定位、产品矩阵、定价、口碑、优劣势' },
  { value: 'literature_review', label: '论文综述', description: '经典理论、近年进展、研究空白、方法论' },
  { value: 'custom', label: '自定义', description: '自由研究，不预设拆分策略' },
] as const;
```
