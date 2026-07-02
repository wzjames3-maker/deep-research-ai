/* ===== Research Template ===== */
export type ResearchTemplate =
  | "tech_research"
  | "competitive_analysis"
  | "literature_review"
  | "custom";

export const TEMPLATE_LABELS: Record<ResearchTemplate, string> = {
  tech_research: "技术调研",
  competitive_analysis: "竞品分析",
  literature_review: "论文综述",
  custom: "自定义",
};

/* ===== Research Status ===== */
export type ResearchStatus =
  | "draft"
  | "confirmed"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export const STATUS_LABELS: Record<ResearchStatus, string> = {
  draft: "草稿",
  confirmed: "已确认",
  running: "进行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const STATUS_COLORS: Record<ResearchStatus, string> = {
  draft: "bg-gray-100 text-gray-700 border-gray-200",
  confirmed: "bg-blue-50 text-blue-700 border-blue-200",
  running: "bg-blue-100 text-blue-800 border-blue-300",
  completed: "bg-green-100 text-green-800 border-green-300",
  failed: "bg-red-100 text-red-800 border-red-300",
  cancelled: "bg-yellow-100 text-yellow-800 border-yellow-300",
};

/* ===== Sub-Agent ===== */
export interface SubAgentPlan {
  name: string;
  goal: string;
  searchDirection: string;
}

export type SubAgentStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface SubAgentResult {
  name: string;
  goal: string;
  status: SubAgentStatus;
  findings: string;
  visitedUrls: string[];
  tokenUsed: number;
}

/* ===== Research ===== */
export interface Research {
  researchId: string;
  topic: string;
  template: string;
  status: ResearchStatus;
  plan: Record<string, unknown> | null;
  planRound: number;
  subAgentResults: SubAgentResult[];
  totalTokens: number;
  createdAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

/* ===== Report (extends Research with reportMarkdown) ===== */
export interface ResearchReport {
  researchId: string;
  topic: string;
  template: string;
  status: string;
  plan: Record<string, unknown> | null;
  reportMarkdown: string | null;
  subAgentResults: SubAgentResult[];
  totalTokens: number;
  createdAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

/* ===== API Response Types ===== */
export interface LoginResponse {
  userId: string;
  username: string;
  token: string;
  expiresIn: number;
}

export interface MeResponse {
  userId: string;
  username: string;
  status: string;
}

export interface TicketResponse {
  ticket: string;
  expiresIn: number;
}

export interface TokenStats {
  todayTokens: number;
  weekTokens: number;
  totalResearches: number;
  avgTokensPerResearch: number;
}

export interface HistoryItem {
  researchId: string;
  topic: string;
  template: string;
  status: string;
  totalTokens: number;
  createdAt: string | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ApiError {
  code: string;
  message: string;
}

/* ===== SSE Events ===== */
export type SSEEventType =
  | "sub_agent_start"
  | "sub_agent_round"
  | "sub_agent_complete"
  | "sub_agent_fail"
  | "aggregation_start"
  | "report_complete"
  | "error"
  | "heartbeat"
  | "plan_confirm";

export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
}
