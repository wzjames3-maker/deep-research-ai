import { useState, useRef, type FormEvent } from "react";
import { toast } from "sonner";
import { researchApi } from "@/api/research";
import type { Research, SubAgentPlan } from "@/types";
import { TEMPLATE_LABELS } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Check, Send, Target, Compass } from "lucide-react";

interface PlanPanelProps {
  research: Research;
  onUpdate: (r: Research) => void;
  onReload: () => void;
}

export default function PlanPanel({ research, onUpdate, onReload }: PlanPanelProps) {
  const [feedback, setFeedback] = useState("");
  const [reviseLoading, setReviseLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: "user" | "ai"; content: string }[]>([]);

  const maxRounds = 10;
  // P1-6: planRound is the current round number (1-based), revision_count = planRound - 1
  const currentRound = research.planRound ?? 1;
  const isMaxRounds = currentRound > maxRounds;

  async function handleRevise(e: FormEvent) {
    e.preventDefault();
    if (!feedback.trim() || reviseLoading) return;
    const userMsg = feedback.trim();
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setFeedback("");
    setReviseLoading(true);
    try {
      const updated = await researchApi.revise(research.researchId, userMsg);
      onUpdate(updated);
      // Extract sub-agents from plan
      const planObj = updated.plan as Record<string, unknown> | null;
      const subAgents = (planObj?.subAgents as SubAgentPlan[]) || [];
      setMessages((m) => [
        ...m,
        { role: "ai", content: `已更新计划，当前共 ${subAgents.length} 个子课题。` },
      ]);
    } catch {
      toast.error("计划修改失败，请重试");
      setMessages((m) => [...m, { role: "ai", content: "修改失败，请重试。" }]);
    } finally {
      setReviseLoading(false);
    }
  }

  const pollRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  async function handleConfirm() {
    setConfirmLoading(true);
    try {
      await researchApi.confirm(research.researchId);
      toast.success("计划已确认，研究开始");
      // 轮询等待 status 变为 running
      pollRef.current = setInterval(async () => {
        try {
          const updated = await researchApi.get(research.researchId);
          if (updated.status !== "draft" && updated.status !== "confirmed") {
            clearInterval(pollRef.current);
            onUpdate(updated); // WorkbenchPage 检测到变化，切换视图
          }
        } catch { /* ignore */ }
      }, 2000);
      // 安全超时：30 秒后停止轮询
      setTimeout(() => { if (pollRef.current) clearInterval(pollRef.current); }, 30000);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      toast.error(error.response?.data?.message || "确认失败");
    } finally {
      setConfirmLoading(false);
    }
  }

  // Extract sub-agents from plan wrapper: { subAgents: [...] }
  const planObj = research.plan as Record<string, unknown> | null;
  const plan: SubAgentPlan[] = (planObj?.subAgents as SubAgentPlan[]) || [];

  return (
    <div className="space-y-6">
      {/* Topic & Meta */}
      <div>
        <h1 className="text-2xl font-bold mb-2">{research.topic}</h1>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span>{TEMPLATE_LABELS[research.template as keyof typeof TEMPLATE_LABELS]}</span>
          <span>·</span>
          <Badge variant="outline" className="text-xs">
            {research.status === "draft" ? "草稿" : "已确认"}
          </Badge>
          <span>·</span>
          <span>第 {currentRound}/{maxRounds} 轮</span>
        </div>
      </div>

      {/* Sub-agent Plan Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Sub-agent 计划</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {plan.map((agent, i) => (
            <Card key={i} className="border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                    {i + 1}
                  </span>
                  {agent.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-start gap-2 text-sm">
                  <Target className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                  <span className="text-muted-foreground">{agent.goal}</span>
                </div>
                <div className="flex items-start gap-2 text-sm">
                  <Compass className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                  <span className="text-muted-foreground">{agent.searchDirection}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Confirm Button */}
      <Button
        size="lg"
        className="w-full"
        onClick={handleConfirm}
        disabled={confirmLoading || plan.length === 0}
      >
        {confirmLoading ? (
          <Loader2 className="animate-spin" />
        ) : (
          <Check className="w-4 h-4" />
        )}
        {confirmLoading ? "确认中..." : "确认计划"}
      </Button>

      {/* Chat Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">修改建议</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Messages */}
          {messages.length > 0 && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleRevise} className="flex gap-2">
            <Textarea
              placeholder={
                isMaxRounds
                  ? "已达到最大修改轮次，请确认计划"
                  : "输入修改建议..."
              }
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="min-h-[40px] resize-none"
              disabled={isMaxRounds || reviseLoading}
              rows={1}
            />
            <Button type="submit" disabled={!feedback.trim() || reviseLoading || isMaxRounds}>
              {reviseLoading ? <Loader2 className="animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </form>

          {isMaxRounds && (
            <p className="text-sm text-muted-foreground text-center">
              已达到最大修改轮次 ({maxRounds})，请确认计划
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
