import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { researchApi } from "@/api/research";
import type { HistoryItem } from "@/types";
import { STATUS_LABELS, STATUS_COLORS, TEMPLATE_LABELS } from "@/types";
import { formatTokens, relativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ArrowLeft, ArrowRight, Trash2, Loader2, Plus, Search } from "lucide-react";

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<HistoryItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadHistory = useCallback(() => {
    setLoading(true);
    researchApi
      .listHistory(page, PAGE_SIZE)
      .then((resp) => {
        setItems(resp.items);
        setTotal(resp.total);
      })
      .catch(() => toast.error("加载历史失败"))
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await researchApi.delete(deleteTarget.researchId);
      toast.success("已删除");
      setDeleteTarget(null);
      // P1-3: 删除后重新加载，确保分页正确
      loadHistory();
    } catch {
      toast.error("删除失败");
    } finally {
      setDeleteLoading(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")}>
              <ArrowLeft className="w-4 h-4" />
              返回
            </Button>
            <Search className="w-5 h-5 text-primary" />
            <span className="font-bold">DeepResearch</span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">研究历史 ({total})</h1>
          <Button onClick={() => navigate("/research/new")}>
            <Plus className="w-4 h-4" />
            新建研究
          </Button>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="text-center py-16">
              <Search className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
              <p className="text-lg font-medium mb-2">还没有研究记录</p>
              <p className="text-muted-foreground mb-6">创建你的第一个研究吧</p>
              <Button onClick={() => navigate("/research/new")}>
                <Plus className="w-4 h-4" />
                开始研究
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="space-y-3">
              {items.map((r) => (
                <Card
                  key={r.researchId}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => navigate(`/research/${r.researchId}`)}
                >
                  <CardContent className="pt-4 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium truncate">{r.topic}</span>
                        <Badge
                          variant="outline"
                          className={`text-xs shrink-0 ${STATUS_COLORS[r.status as keyof typeof STATUS_COLORS]}`}
                        >
                          {STATUS_LABELS[r.status as keyof typeof STATUS_LABELS]}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{TEMPLATE_LABELS[r.template as keyof typeof TEMPLATE_LABELS]}</span>
                        {r.totalTokens > 0 && <span>{formatTokens(r.totalTokens)} tokens</span>}
                        <span>{relativeTime(r.createdAt)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteTarget(r);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                      <ArrowRight className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  上一页
                </Button>
                <span className="text-sm text-muted-foreground">
                  共 {total} 条，第 {page}/{totalPages} 页
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  下一页
                </Button>
              </div>
            )}
          </>
        )}
      </main>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确定删除「{deleteTarget?.topic}」？</DialogTitle>
            <DialogDescription>
              删除后数据仍可在数据库中恢复。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteLoading}>
              {deleteLoading && <Loader2 className="animate-spin" />}
              确定删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
