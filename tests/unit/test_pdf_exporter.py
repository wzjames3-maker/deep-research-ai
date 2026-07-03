"""Tests for PDF exporter service."""

import sys
import pytest
from unittest.mock import patch, MagicMock
from src.errors import ExportFailedError


# Create a mock weasyprint module if not installed
@pytest.fixture(autouse=True)
def _ensure_weasyprint_mock():
    """Ensure weasyprint is importable for tests."""
    if "weasyprint" not in sys.modules:
        mock_mod = MagicMock()
        mock_mod.HTML = MagicMock()
        sys.modules["weasyprint"] = mock_mod
        yield
        del sys.modules["weasyprint"]
    else:
        yield


class TestPdfExporter:
    """Test pdf_exporter module."""

    @pytest.mark.asyncio
    async def test_empty_markdown_raises(self):
        from src.services.pdf_exporter import export_report_to_pdf

        with pytest.raises(ExportFailedError, match="报告内容为空"):
            await export_report_to_pdf("")

    @pytest.mark.asyncio
    async def test_none_markdown_raises(self):
        from src.services.pdf_exporter import export_report_to_pdf

        with pytest.raises(ExportFailedError, match="报告内容为空"):
            await export_report_to_pdf(None)

    @pytest.mark.asyncio
    async def test_markdown_to_html_basic(self):
        from src.services.pdf_exporter import _markdown_to_html

        html = _markdown_to_html("# Hello\n\nWorld", topic="测试")
        assert "测试" in html
        assert "<!DOCTYPE html>" in html
        assert "charset" in html

    @pytest.mark.asyncio
    async def test_markdown_to_html_with_citations(self):
        from src.services.pdf_exporter import _markdown_to_html

        citations = [
            {"citationNumber": 1, "url": "https://example.com", "title": "Example"},
        ]
        html = _markdown_to_html("# Report", citations=citations)
        assert "参考文献" in html
        assert "https://example.com" in html
        assert "[1]" in html

    @pytest.mark.asyncio
    async def test_build_citation_html_empty(self):
        from src.services.pdf_exporter import _build_citation_html

        assert _build_citation_html([]) == ""
        assert _build_citation_html(None) == ""

    @pytest.mark.asyncio
    async def test_build_citation_html_with_items(self):
        from src.services.pdf_exporter import _build_citation_html

        citations = [
            {"citationNumber": 1, "url": "https://a.com", "title": "A"},
            {"citationNumber": 2, "url": "https://b.com", "title": ""},
        ]
        html = _build_citation_html(citations)
        assert "[1]" in html
        assert "[2]" in html
        assert "https://a.com" in html
        assert "https://b.com" in html

    @pytest.mark.asyncio
    async def test_export_with_weasyprint_mock(self):
        from src.services.pdf_exporter import export_report_to_pdf

        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-1.4 fake pdf content"

        mock_html_class = MagicMock(return_value=mock_html_instance)

        import weasyprint
        original = weasyprint.HTML
        weasyprint.HTML = mock_html_class
        try:
            result = await export_report_to_pdf(
                report_markdown="# Report\n\nContent here.",
                topic="Test Topic",
                citations=[{"citationNumber": 1, "url": "https://x.com", "title": "X"}],
            )
        finally:
            weasyprint.HTML = original

        assert result == b"%PDF-1.4 fake pdf content"
        mock_html_instance.write_pdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_weasyprint_failure(self):
        from src.services.pdf_exporter import export_report_to_pdf

        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.side_effect = RuntimeError("weasyprint error")

        mock_html_class = MagicMock(return_value=mock_html_instance)

        import weasyprint
        original = weasyprint.HTML
        weasyprint.HTML = mock_html_class
        try:
            with pytest.raises(ExportFailedError, match="PDF 生成失败"):
                await export_report_to_pdf("# Report")
        finally:
            weasyprint.HTML = original
