import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { researchApi } from "@/api/research";
import type { Research, ResearchReport } from "@/types";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Search } from "lucide-react";
import PlanPanel from "@/components/Research/PlanPanel";
import ProgressDashboard from "@/components/Research/ProgressDashboard";
import ReportView from "@/components/Research/ReportView";

export default function WorkbenchPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [research, setResearch] = useState<Research | null>(null);
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadResearch = useCallback(() => {
    if (!id) return;
    researchApi
      .get(id)
      .then((r) => {
        setResearch(r);
        setError(null);
      })
      .catch(() => setError("加载研究详情失败"))
      .finally(() => setLoading(false));
  }, [id]);

  // P0-4: Load report data when status is completed/cancelled
  const loadReport = useCallback(() => {
    if (!id) return;
    researchApi
      .getReport(id)
      .then(setReport)
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    loadResearch();
  }, [loadResearch]);

  // When research becomes completed/cancelled, load report
  useEffect(() => {
    if (research && (research.status === "completed" || research.status === "cancelled")) {
      loadReport();
    }
  }, [research, loadReport]);

  if (loading) {
    return (
      <div className="min-h-screen bg-muted/30">
        <header className="border-b bg-background">
          <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              <ArrowLeft className="w-4 h-4" />
              返回
            </Button>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-8 space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-32 w-full" />
        </main>
      </div>
    );
  }

  if (error || !research) {
    return (
      <div className="min-h-screen bg-muted/30">
        <header className="border-b bg-background">
          <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              <ArrowLeft className="w-4 h-4" />
              返回
            </Button>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-8 text-center">
          <p className="text-destructive mb-4">{error || "研究不存在"}</p>
          <Button onClick={() => navigate("/dashboard")}>返回仪表盘</Button>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              <ArrowLeft className="w-4 h-4" />
              返回
            </Button>
            <Search className="w-5 h-5 text-primary" />
            <span className="font-bold text-lg">DeepResearch</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {(research.status === "draft" || research.status === "confirmed") && (
          <PlanPanel research={research} onUpdate={setResearch} onReload={loadResearch} />
        )}
        {research.status === "running" && (
          <ProgressDashboard research={research} onUpdate={setResearch} />
        )}
        {(research.status === "completed" || research.status === "cancelled") && report && (
          <ReportView research={research} report={report} />
        )}
        {(research.status === "completed" || research.status === "cancelled") && !report && (
          <div className="text-center py-16">
            <Skeleton className="h-48 w-full" />
          </div>
        )}
        {research.status === "failed" && (
          <div className="text-center py-16 space-y-4">
            <p className="text-2xl font-semibold text-destructive">研究失败</p>
            <p className="text-muted-foreground">研究过程中发生了错误，请重新创建</p>
            <Button onClick={() => navigate(`/research/new?topic=${encodeURIComponent(research.topic)}`)}>
              重新研究
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
