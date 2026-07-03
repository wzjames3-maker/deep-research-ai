import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useState, useCallback } from "react";
import type { Research, ResearchReport, SubAgentPlan, Citation } from "@/types";
import { TEMPLATE_LABELS } from "@/types";
import { formatTokens } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Copy, FileText, RotateCcw, Quote, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CitationPanel from "./CitationPanel";
import { researchApi } from "@/api/research";

interface ReportViewProps {
  research: Research;
  report: ResearchReport;
}

function stripMarkdown(md: string): string {
  return md
    .replace(/#{1,6}\s?/g, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .replace(/\[(.+?)\]\(.+?\)/g, "$1")
    .replace(/^\s*[-*+]\s/gm, "")
    .replace(/^\s*\d+\.\s/gm, "");
}

/**
 * Process text to make [N] citation markers clickable.
 * Matches patterns like [1], [2], [1][3], [1, 2].
 */
function renderTextWithCitations(
  text: string,
  onCitationClick: (num: number) => void,
) {
  // Match [N] patterns (citation references)
  const parts = text.split(/(\[\d+\])/g);
  if (parts.length === 1) return text;

  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const num = parseInt(match[1], 10);
      return (
        <button
          key={i}
          onClick={(e) => {
            e.preventDefault();
            onCitationClick(num);
          }}
          className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-primary/15 text-primary text-[10px] font-bold hover:bg-primary/30 transition-colors align-super mx-0.5"
          title={`引用 [${num}]`}
        >
          {num}
        </button>
      );
    }
    return part;
  });
}

function MarkdownRenderer({
  content,
  onCitationClick,
}: {
  content: string;
  onCitationClick?: (num: number) => void;
}) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children }) => {
          // Check if this is a [N] link that should be a citation
          const text = String(children);
          const citationMatch = text.match(/^\[(\d+)\]$/);
          if (citationMatch && onCitationClick) {
            const num = parseInt(citationMatch[1], 10);
            return (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  onCitationClick(num);
                }}
                className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-primary/15 text-primary text-[10px] font-bold hover:bg-primary/30 transition-colors align-super mx-0.5"
                title={`引用 [${num}]`}
              >
                {num}
              </button>
            );
          }
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
              {children}
            </a>
          );
        },
        p: ({ children }) => {
          // Process text nodes for [N] patterns
          if (onCitationClick) {
            const processed = React.Children.map(children, (child) => {
              if (typeof child === "string") {
                return renderTextWithCitations(child, onCitationClick);
              }
              return child;
            });
            return <p className="mb-3 leading-relaxed">{processed}</p>;
          }
          return <p className="mb-3 leading-relaxed">{children}</p>;
        },
        table: ({ children }) => (
          <div className="overflow-x-auto my-4">
            <table className="border-collapse border border-border w-full">
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-border px-3 py-2 bg-muted font-semibold text-left">{children}</th>
        ),
        td: ({ children }) => (
          <td className="border border-border px-3 py-2">{children}</td>
        ),
        h1: ({ children }) => <h1 className="text-2xl font-bold mt-6 mb-3">{children}</h1>,
        h2: ({ children }) => <h2 className="text-xl font-bold mt-5 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-lg font-semibold mt-4 mb-2">{children}</h3>,
        ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
        code: ({ children, className }) => {
          const isBlock = className?.includes("language-");
          if (isBlock) {
            return (
              <pre className="bg-muted rounded-lg p-4 overflow-x-auto mb-4 text-sm">
                <code>{children}</code>
              </pre>
            );
          }
          return <code className="bg-muted px-1.5 py-0.5 rounded text-sm">{children}</code>;
        },
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-primary/30 pl-4 italic text-muted-foreground my-4">
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export default function ReportView({ research, report }: ReportViewProps) {
  const navigate = useNavigate();
  const isCancelled = research.status === "cancelled";
  const reportMarkdown = report.reportMarkdown;
  const hasReport = !!reportMarkdown;
  const citations = report.citations || [];
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);

  const handleCitationClick = useCallback((num: number) => {
    setActiveCitation(num);
    // Scroll to citation in panel
    const el = document.getElementById(`citation-${num}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  async function exportPdf() {
    setExporting(true);
    try {
      const blob = await researchApi.exportPdf(research.researchId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${research.topic.slice(0, 30)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("PDF 导出成功");
    } catch {
      toast.error("PDF 导出失败");
    } finally {
      setExporting(false);
    }
  }

  async function copyMarkdown() {
    if (!reportMarkdown) return;
    try {
      await navigator.clipboard.writeText(reportMarkdown);
      toast.success("已复制 Markdown");
    } catch {
      toast.error("复制失败，浏览器可能不支持 Clipboard API");
    }
  }

  async function copyPlainText() {
    if (!reportMarkdown) return;
    try {
      const plain = stripMarkdown(reportMarkdown);
      await navigator.clipboard.writeText(plain);
      toast.success("已复制纯文本");
    } catch {
      toast.error("复制失败");
    }
  }

  // P1-4: Use completedAt - startedAt for elapsed time
  let elapsedText = "—";
  const startTime = report.startedAt || report.createdAt;
  if (report.completedAt && startTime) {
    const startMs = new Date(startTime).getTime();
    const endMs = new Date(report.completedAt).getTime();
    const elapsedMs = Math.max(0, endMs - startMs);
    const mins = Math.floor(elapsedMs / 60_000);
    const secs = Math.floor((elapsedMs % 60_000) / 1000);
    elapsedText = `${mins}:${secs.toString().padStart(2, "0")}`;
  } else if (startTime) {
    const elapsedMs = Date.now() - new Date(startTime).getTime();
    const mins = Math.floor(elapsedMs / 60_000);
    const secs = Math.floor((elapsedMs % 60_000) / 1000);
    elapsedText = `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  // Extract sub-agents from plan wrapper
  const planObj = research.plan as Record<string, unknown> | null;
  const plan: SubAgentPlan[] = (planObj?.subAgents as SubAgentPlan[]) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-2">
          {isCancelled ? "部分报告: " : "研究报告: "}{research.topic}
        </h1>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span>{TEMPLATE_LABELS[research.template as keyof typeof TEMPLATE_LABELS]}</span>
          <span>·</span>
          <span>总耗时: {elapsedText}</span>
          <span>·</span>
          <span>{formatTokens(research.totalTokens)} tokens</span>
          {isCancelled && (
            <>
              <span>·</span>
              <Badge variant="outline" className="text-yellow-600 border-yellow-300">已取消</Badge>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="summary" className="w-full">
        <TabsList>
          <TabsTrigger value="plan">研究计划</TabsTrigger>
          <TabsTrigger value="agents">Sub-agent 结果</TabsTrigger>
          <TabsTrigger value="summary">研究汇总</TabsTrigger>
          {citations.length > 0 && (
            <TabsTrigger value="citations" className="gap-1">
              <Quote className="w-3.5 h-3.5" />
              引用 ({citations.length})
            </TabsTrigger>
          )}
        </TabsList>

        {/* Tab 1: Plan */}
        <TabsContent value="plan">
          <Card>
            <CardContent className="pt-4">
              <div className="space-y-3">
                {plan.map((agent, i) => (
                  <div key={i} className="p-3 rounded-lg border">
                    <div className="font-medium mb-1">{i + 1}. {agent.name}</div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <p>目标: {agent.goal}</p>
                      <p>搜索方向: {agent.searchDirection}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Sub-agent Results */}
        <TabsContent value="agents">
          <div className="space-y-4">
            {(report.subAgentResults || []).map((agent, i) => (
              <Card key={i}>
                <CardContent className="pt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium">{agent.name}</span>
                      <span className="text-sm text-muted-foreground ml-2">{agent.goal}</span>
                    </div>
                    <Badge variant="outline">
                      {agent.tokenUsed > 0 ? formatTokens(agent.tokenUsed) : "—"} tokens
                    </Badge>
                  </div>

                  {agent.findings && (
                    <div className="prose prose-sm max-w-none">
                      <MarkdownRenderer content={agent.findings} />
                    </div>
                  )}

                  {agent.visitedUrls && agent.visitedUrls.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">来源链接:</p>
                      <div className="flex flex-wrap gap-1">
                        {agent.visitedUrls.map((url, j) => (
                          <a
                            key={j}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 hover:underline truncate max-w-[300px] block"
                          >
                            [{j + 1}] {url}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Tab 3: Summary Report */}
        <TabsContent value="summary">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className={citations.length > 0 ? "lg:col-span-2" : ""}>
              <Card>
                <CardContent className="pt-4">
                  {hasReport ? (
                    <div className="prose prose-sm max-w-none">
                      <MarkdownRenderer
                        content={reportMarkdown!}
                        onCitationClick={handleCitationClick}
                      />
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
                      <p>
                        {isCancelled
                          ? "研究被取消，可能没有生成完整报告"
                          : "暂无报告内容"}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
            {citations.length > 0 && (
              <div className="hidden lg:block">
                <CitationPanel
                  citations={citations}
                  activeCitation={activeCitation}
                  onCitationClick={handleCitationClick}
                />
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 4: Citations (mobile) */}
        {citations.length > 0 && (
          <TabsContent value="citations">
            <CitationPanel
              citations={citations}
              activeCitation={activeCitation}
              onCitationClick={handleCitationClick}
            />
          </TabsContent>
        )}
      </Tabs>

      {/* Actions */}
      {hasReport && (
        <div className="flex gap-3">
          <Button variant="outline" onClick={exportPdf} disabled={exporting}>
            <Download className="w-4 h-4" />
            {exporting ? "导出中..." : "导出 PDF"}
          </Button>
          <Button variant="outline" onClick={copyMarkdown}>
            <Copy className="w-4 h-4" />
            复制 Markdown
          </Button>
          <Button variant="outline" onClick={copyPlainText}>
            <FileText className="w-4 h-4" />
            复制纯文本
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate(`/research/new?topic=${encodeURIComponent(research.topic)}`)}
          >
            <RotateCcw className="w-4 h-4" />
            重新研究
          </Button>
        </div>
      )}
    </div>
  );
}
