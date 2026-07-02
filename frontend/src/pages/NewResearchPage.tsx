import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { researchApi } from "@/api/research";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import type { ResearchTemplate } from "@/types";
import { TEMPLATE_LABELS } from "@/types";
import { Loader2, ArrowLeft, Code, Search, BookOpen, Pencil } from "lucide-react";

const TEMPLATES: { value: ResearchTemplate; icon: typeof Code; desc: string }[] = [
  { value: "tech_research", icon: Code, desc: "技术原理 → 生态 → 竞品 → 应用 → 趋势" },
  { value: "competitive_analysis", icon: Search, desc: "市场 → 产品 → 定价 → 口碑 → 优劣势" },
  { value: "literature_review", icon: BookOpen, desc: "经典 → 进展 → 争议 → 空白 → 方法论" },
  { value: "custom", icon: Pencil, desc: "自由拆分 3-5 个合理角度" },
];

export default function NewResearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [topic, setTopic] = useState(searchParams.get("topic") || "");
  const [template, setTemplate] = useState<ResearchTemplate | null>(null);
  const [loading, setLoading] = useState(false);

  const canSubmit = topic.trim().length > 0 && template && !loading;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit || !template) return;
    setLoading(true);
    try {
      const research = await researchApi.create(topic.trim(), template);
      toast.success("研究已创建");
      navigate(`/research/${research.researchId}`);
    } catch (err: unknown) {
      const error = err as { response?: { status: number; data?: { code?: string; message?: string } } };
      const status = error.response?.status;
      const code = error.response?.data?.code;
      if (status === 409 || code === "RESEARCH_IN_PROGRESS") {
        toast.error("当前有一个进行中的研究");
      } else if (status === 504 || code === "PLAN_GENERATION_TIMEOUT") {
        toast.error("计划生成超时，请重试");
      } else if (status === 500 || code === "PLAN_GENERATION_FAILED") {
        toast.error("计划生成失败，请检查网络后重试");
      } else {
        toast.error(error.response?.data?.message || "创建失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center">
          <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
            <ArrowLeft className="w-4 h-4" />
            返回仪表盘
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Topic Input */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">输入研究主题</h2>
            <Textarea
              placeholder="输入研究主题，描述你的研究目标，越具体效果越好..."
              value={topic}
              onChange={(e) => setTopic(e.target.value.slice(0, 500))}
              className="min-h-[100px] text-base"
              autoFocus
            />
            <div className="flex justify-end text-sm text-muted-foreground">
              {topic.length}/500
            </div>
          </div>

          {/* Template Selector */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">选择研究模板</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {TEMPLATES.map((t) => {
                const Icon = t.icon;
                const selected = template === t.value;
                return (
                  <Card
                    key={t.value}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      selected
                        ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                        : "hover:border-primary/50"
                    }`}
                    onClick={() => setTemplate(t.value)}
                  >
                    <CardContent className="pt-4 text-center space-y-2">
                      <Icon className={`w-8 h-8 mx-auto ${selected ? "text-primary" : "text-muted-foreground"}`} />
                      <p className="font-medium text-sm">{TEMPLATE_LABELS[t.value]}</p>
                      <p className="text-xs text-muted-foreground leading-tight">{t.desc}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Submit */}
          <Button type="submit" size="lg" className="w-full" disabled={!canSubmit}>
            {loading && <Loader2 className="animate-spin" />}
            {loading ? "正在生成研究计划..." : "开始研究"}
          </Button>
        </form>
      </main>
    </div>
  );
}
