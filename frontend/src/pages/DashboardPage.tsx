import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "@/contexts/AuthContext";
import { researchApi } from "@/api/research";
import type { TokenStats, HistoryItem } from "@/types";
import { STATUS_LABELS, STATUS_COLORS, TEMPLATE_LABELS } from "@/types";
import { formatTokens, relativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { LogOut, Plus, History, ArrowRight, Search } from "lucide-react";

export default function DashboardPage() {
  const { username, logout } = useAuthContext();
  const navigate = useNavigate();
  const [stats, setStats] = useState<TokenStats | null>(null);
  const [recent, setRecent] = useState<HistoryItem[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingRecent, setLoadingRecent] = useState(true);

  useEffect(() => {
    researchApi.getTokenStats().then(setStats).catch(() => {}).finally(() => setLoadingStats(false));
    researchApi.listHistory(1, 5).then((r) => setRecent(r.items)).catch(() => {}).finally(() => setLoadingRecent(false));
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-muted/30">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-primary" />
            <span className="font-bold text-lg">DeepResearch</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">{username}</span>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="w-4 h-4" />
              退出
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {loadingStats
            ? Array.from({ length: 4 }).map((_, i) => (
                <Card key={i}>
                  <CardContent className="pt-6">
                    <Skeleton className="h-8 w-20 mb-2" />
                    <Skeleton className="h-4 w-16" />
                  </CardContent>
                </Card>
              ))
            : [
                { label: "今日消耗", value: formatTokens(stats?.todayTokens ?? 0) },
                { label: "本周消耗", value: formatTokens(stats?.weekTokens ?? 0) },
                { label: "总研究数", value: String(stats?.totalResearches ?? 0) },
                { label: "平均消耗", value: formatTokens(stats?.avgTokensPerResearch ?? 0) },
              ].map((s) => (
                <Card key={s.label}>
                  <CardContent className="pt-6">
                    <p className="text-2xl font-bold">{s.value}</p>
                    <p className="text-sm text-muted-foreground">{s.label}</p>
                  </CardContent>
                </Card>
              ))}
        </div>

        {/* Quick Actions */}
        <div className="flex gap-4">
          <Button onClick={() => navigate("/research/new")}>
            <Plus className="w-4 h-4" />
            新建研究
          </Button>
          <Button variant="outline" onClick={() => navigate("/research/history")}>
            <History className="w-4 h-4" />
            查看全部历史
          </Button>
        </div>

        {/* Recent Researches */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">最近研究</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingRecent ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : recent.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <p className="mb-4">还没有研究记录</p>
                <Button onClick={() => navigate("/research/new")}>
                  <Plus className="w-4 h-4" />
                  开始第一次研究
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {recent.map((r) => (
                  <div
                    key={r.researchId}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer transition-colors"
                    onClick={() => navigate(`/research/${r.researchId}`)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium truncate">{r.topic}</span>
                        <Badge variant="outline" className={`text-xs ${STATUS_COLORS[r.status as keyof typeof STATUS_COLORS]}`}>
                          {STATUS_LABELS[r.status as keyof typeof STATUS_LABELS]}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{TEMPLATE_LABELS[r.template as keyof typeof TEMPLATE_LABELS]}</span>
                        {r.totalTokens > 0 && <span>{formatTokens(r.totalTokens)} tokens</span>}
                        <span>{relativeTime(r.createdAt)}</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 ml-2" />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
