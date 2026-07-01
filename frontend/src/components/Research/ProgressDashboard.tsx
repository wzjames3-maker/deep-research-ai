import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { researchApi } from "@/api/research";
import { useSSE } from "@/hooks/useSSE";
import type { Research, SubAgentResult } from "@/types";
import { formatTokens, formatElapsed } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CheckCircle,
  Loader2,
  Clock,
  XCircle,
  MinusCircle,
  Square,
} from "lucide-react";

interface AgentState extends SubAgentResult {
  subAgentId?: string;
  round?: number;
  errorMessage?: string;
}

interface ProgressDashboardProps {
  research: Research;
  onUpdate: (r: Research) => void;
}

const STATUS_ICON: Record<string, typeof Clock> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: MinusCircle,
};

const STATUS_STYLE: Record<string, string> = {
  pending: "border-gray-200 text-gray-500",
  running: "border-blue-300 text-blue-600",
  completed: "border-green-300 text-green-600",
  failed: "border-red-300 text-red-600",
  cancelled: "border-gray-200 text-gray-400 line-through",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "等待中",
  running: "搜索中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
  aggregating: "汇总中",
};

export default function ProgressDashboard({ research, onUpdate }: ProgressDashboardProps) {
  // Initialize agents from subAgentResults
  const [agents, setAgents] = useState<AgentState[]>(() =>
    (research.subAgentResults || []).map((a) => ({ ...a }))
  );
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [elapsed, setElapsed] = useState(formatElapsed(research.createdAt));
  const [isAggregating, setIsAggregating] = useState(false);

  // Timer
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(formatElapsed(research.createdAt));
    }, 1000);
    return () => clearInterval(interval);
  }, [research.createdAt]);

  // Sync agents when research changes
  useEffect(() => {
    setAgents(
      (research.subAgentResults || []).map((a) => ({ ...a }))
    );
  }, [research]);

  const reloadResearch = useCallback(() => {
    researchApi.get(research.researchId).then((r) => {
      onUpdate(r);
      setAgents((r.subAgentResults || []).map((a) => ({ ...a })));
    });
  }, [research.researchId, onUpdate]);

  // P1-7: Use subAgentId for matching agents (not name, which may be duplicated)
  useSSE(research.researchId, {
    onSubAgentStart: (data) => {
      const agentId = data.subAgentId as string;
      const name = data.name as string;
      setAgents((prev) =>
        prev.map((a) =>
          (a.subAgentId && a.subAgentId === agentId) || a.name === name
            ? { ...a, status: "running", subAgentId: agentId }
            : a
        )
      );
    },
    onSubAgentRound: (data) => {
      const agentId = data.subAgentId as string;
      const round = data.round as number;
      setAgents((prev) =>
        prev.map((a) =>
          a.subAgentId === agentId
            ? { ...a, round }
            : a
        )
      );
    },
    onSubAgentComplete: (data) => {
      const agentId = data.subAgentId as string;
      const name = data.name as string;
      const preview = (data.preview as string) || "";
      const tokenUsed = (data.tokenUsed as number) || 0;
      reloadResearch();
      setAgents((prev) =>
        prev.map((a) =>
          (a.subAgentId && a.subAgentId === agentId) || a.name === name
            ? { ...a, status: "completed", findings: preview.slice(0, 200), tokenUsed }
            : a
        )
      );
    },
    onSubAgentFail: (data) => {
      const agentId = data.subAgentId as string;
      const name = data.name as string;
      const errorMsg = (data.error as string) || "未知错误";
      setAgents((prev) =>
        prev.map((a) =>
          (a.subAgentId && a.subAgentId === agentId) || a.name === name
            ? { ...a, status: "failed", errorMessage: errorMsg }
            : a
        )
      );
    },
    onAggregationStart: () => {
      setIsAggregating(true);
    },
    onReportComplete: () => {
      setIsAggregating(false);
      toast.success("研究报告已生成");
      reloadResearch();
    },
    onError: (data) => {
      toast.error((data.message as string) || "研究过程中发生错误");
    },
  });

  const completedCount = agents.filter((a) => a.status === "completed").length;
  const totalTokens = agents.reduce((sum, a) => sum + (a.tokenUsed || 0), 0);

  async function handleCancel() {
    setCancelLoading(true);
    try {
      await researchApi.cancel(research.researchId);
      toast.success("研究已停止");
      reloadResearch();
    } catch {
      toast.error("停止失败");
    } finally {
      setCancelLoading(false);
      setCancelDialogOpen(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-2">正在研究: {research.topic}</h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>已完成: {completedCount}/{agents.length}</span>
          <span>·</span>
          <span>总耗时: {elapsed}</span>
          <span>·</span>
          <span>{formatTokens(totalTokens)} tokens</span>
        </div>
      </div>

      {/* Aggregation Progress Card */}
      {isAggregating && (
        <Card className="border-purple-300 bg-purple-50/50">
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm">正在生成研究报告</span>
              <Badge variant="outline" className="border-purple-300 text-purple-600">
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                汇总中
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              正在汇总 {completedCount} 个子课题的研究结果，生成最终报告…
            </p>
          </CardContent>
        </Card>
      )}

      {/* Agent Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => {
          const Icon = STATUS_ICON[agent.status] || Clock;
          const style = STATUS_STYLE[agent.status] || "";
          const isRunning = agent.status === "running";

          return (
            <Card key={agent.subAgentId || agent.name} className={style}>
              <CardContent className="pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{agent.name}</span>
                  <Badge variant="outline" className={style}>
                    <Icon className={`w-3 h-3 mr-1 ${isRunning ? "animate-spin" : ""}`} />
                    {STATUS_LABEL[agent.status]}
                  </Badge>
                </div>

                <p className="text-xs text-muted-foreground">{agent.goal}</p>

                {agent.status === "running" && agent.round && (
                  <div className="text-xs text-muted-foreground">
                    <span>第 {agent.round}/2 轮</span>
                  </div>
                )}

                {agent.status === "completed" && agent.tokenUsed > 0 && (
                  <div className="text-xs text-muted-foreground">
                    {formatTokens(agent.tokenUsed)} tokens
                  </div>
                )}

                {agent.status === "completed" && agent.findings && (
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {agent.findings.slice(0, 200)}...
                  </p>
                )}

                {agent.status === "failed" && agent.errorMessage && (
                  <p className="text-xs text-destructive">{agent.errorMessage}</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Cancel Button */}
      <Button
        variant="destructive"
        className="w-full"
        onClick={() => setCancelDialogOpen(true)}
      >
        <Square className="w-4 h-4" />
        停止研究
      </Button>

      {/* Cancel Confirmation Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确定停止当前研究？</DialogTitle>
            <DialogDescription>
              已完成的结果将保留。停止后可以查看已有的部分报告。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleCancel} disabled={cancelLoading}>
              {cancelLoading && <Loader2 className="animate-spin" />}
              确定停止
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
