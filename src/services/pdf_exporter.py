"""PDF Export Service: Markdown → HTML → PDF using weasyprint.

Converts research report markdown (with citations) into a professional PDF document.
"""

import structlog
from src.errors import ExportFailedError

logger = structlog.get_logger()


# CSS styles for the PDF report
_PDF_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {
        content: counter(page) " / " counter(pages);
        font-size: 9pt;
        color: #888;
    }
}
body {
    font-family: "Noto Sans CJK SC", "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #222;
}
h1 {
    font-size: 22pt;
    color: #1a1a2e;
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 6pt;
    margin-top: 0;
}
h2 {
    font-size: 16pt;
    color: #16213e;
    margin-top: 24pt;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4pt;
}
h3 {
    font-size: 13pt;
    color: #0f3460;
    margin-top: 16pt;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
}
th, td {
    border: 1px solid #ccc;
    padding: 6pt 10pt;
    text-align: left;
}
th {
    background-color: #f5f5f5;
    font-weight: bold;
}
blockquote {
    border-left: 3px solid #1a1a2e;
    padding-left: 12pt;
    color: #555;
    font-style: italic;
    margin: 12pt 0;
}
code {
    background-color: #f4f4f4;
    padding: 1pt 4pt;
    border-radius: 2pt;
    font-size: 10pt;
}
pre code {
    display: block;
    padding: 10pt;
    overflow-x: auto;
}
a {
    color: #2563eb;
    text-decoration: none;
}
.references {
    font-size: 9pt;
    color: #555;
    margin-top: 24pt;
    border-top: 1px solid #ddd;
    padding-top: 12pt;
}
.meta {
    font-size: 9pt;
    color: #888;
    margin-bottom: 20pt;
}
"""


def _build_citation_html(citations: list[dict]) -> str:
    """Build HTML for citation references section."""
    if not citations:
        return ""
    items = []
    for c in citations:
        url = c.get("url", "")
        title = c.get("title", "") or url
        num = c.get("citationNumber", c.get("citation_number", 0))
        items.append(f'<p>[{num}] <a href="{url}">{title}</a> — <span style="font-size:8pt;color:#888">{url}</span></p>')
    return f'<div class="references"><h2>参考文献</h2>{"".join(items)}</div>'


def _markdown_to_html(markdown_text: str, topic: str = "", citations: list[dict] | None = None) -> str:
    """Convert markdown to full HTML document."""
    try:
        import markdown as md_lib
        html_body = md_lib.markdown(
            markdown_text,
            extensions=["tables", "fenced_code", "toc"],
        )
    except ImportError:
        # Fallback: basic conversion
        import re
        html_body = markdown_text
        html_body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
        html_body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html_body)
        html_body = html_body.replace("\n\n", "<br/><br/>")

    citation_html = _build_citation_html(citations or [])

    meta_html = ""
    if topic:
        meta_html = f'<div class="meta"><p>研究主题: {topic}</p></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>{_PDF_CSS}</style>
</head>
<body>
{meta_html}
{html_body}
{citation_html}
</body>
</html>"""


async def export_report_to_pdf(
    report_markdown: str,
    topic: str = "",
    citations: list[dict] | None = None,
) -> bytes:
    """Generate PDF from report markdown.

    Args:
        report_markdown: The markdown report content
        topic: Research topic (for metadata)
        citations: List of citation dicts with citationNumber, url, title

    Returns:
        PDF file bytes

    Raises:
        ExportFailedError: If PDF generation fails
    """
    if not report_markdown:
        raise ExportFailedError("报告内容为空，无法导出 PDF")

    try:
        html_content = _markdown_to_html(report_markdown, topic, citations)

        # Import weasyprint (lazy, only when exporting)
        from weasyprint import HTML

        pdf_bytes = HTML(string=html_content).write_pdf()
        logger.info(
            "pdf_export_success",
            topic=topic[:50],
            pdf_size=len(pdf_bytes),
            citation_count=len(citations or []),
        )
        return pdf_bytes

    except ImportError:
        logger.error("weasyprint_not_installed")
        raise ExportFailedError("PDF 导出依赖未安装 (weasyprint)")
    except ExportFailedError:
        raise
    except Exception as e:
        logger.error("pdf_export_failed", error=str(e))
        raise ExportFailedError(f"PDF 生成失败: {e}")
