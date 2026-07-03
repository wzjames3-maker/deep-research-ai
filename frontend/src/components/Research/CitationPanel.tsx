import type { Citation } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";

interface CitationPanelProps {
  citations: Citation[];
  activeCitation: number | null;
  onCitationClick: (num: number) => void;
}

export default function CitationPanel({
  citations,
  activeCitation,
  onCitationClick,
}: CitationPanelProps) {
  if (!citations || citations.length === 0) {
    return (
      <Card className="sticky top-4">
        <CardContent className="pt-4">
          <p className="text-sm text-muted-foreground text-center py-4">
            暂无引用来源
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="sticky top-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
      <CardContent className="pt-4">
        <h3 className="font-semibold text-sm mb-3">
          引用来源 ({citations.length})
        </h3>
        <div className="space-y-2">
          {citations.map((c) => (
            <div
              key={c.citationNumber}
              id={`citation-${c.citationNumber}`}
              className={`p-2 rounded-lg border text-xs cursor-pointer transition-colors ${
                activeCitation === c.citationNumber
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
              onClick={() => onCitationClick(c.citationNumber)}
            >
              <div className="flex items-start gap-1.5">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-bold shrink-0">
                  {c.citationNumber}
                </span>
                <div className="min-w-0 flex-1">
                  {c.title && (
                    <p className="font-medium truncate">{c.title}</p>
                  )}
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-blue-600 hover:underline truncate"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-3 h-3 shrink-0" />
                    <span className="truncate">{c.url}</span>
                  </a>
                  {c.sourceAgent && (
                    <p className="text-muted-foreground mt-0.5">
                      来源: {c.sourceAgent}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
