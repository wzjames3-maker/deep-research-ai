"""Tests for citation system: model, repo, and research_graph integration."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.research_graph import _collect_citations


# ---------------------------------------------------------------------------
# _collect_citations helper tests
# ---------------------------------------------------------------------------


class TestCollectCitations:
    """Test the _collect_citations helper function."""

    def test_empty_results(self):
        records, text = _collect_citations([])
        assert records == []
        assert text == ""

    def test_single_agent_single_url(self):
        results = [
            {"name": "Agent1", "visited_urls": ["https://example.com/1"]},
        ]
        records, text = _collect_citations(results)
        assert len(records) == 1
        assert records[0]["citation_number"] == 1
        assert records[0]["url"] == "https://example.com/1"
        assert records[0]["source_agent"] == "Agent1"
        assert "[1] https://example.com/1" in text

    def test_multiple_agents_dedup_urls(self):
        results = [
            {"name": "Agent1", "visited_urls": ["https://a.com", "https://b.com"]},
            {"name": "Agent2", "visited_urls": ["https://b.com", "https://c.com"]},
        ]
        records, text = _collect_citations(results)
        assert len(records) == 3  # b.com deduplicated
        urls = [r["url"] for r in records]
        assert "https://a.com" in urls
        assert "https://b.com" in urls
        assert "https://c.com" in urls
        # b.com should be assigned to Agent1 (first seen)
        b_record = next(r for r in records if r["url"] == "https://b.com")
        assert b_record["source_agent"] == "Agent1"

    def test_empty_urls_skipped(self):
        results = [
            {"name": "Agent1", "visited_urls": ["", None, "https://ok.com"]},
        ]
        records, text = _collect_citations(results)
        assert len(records) == 1
        assert records[0]["url"] == "https://ok.com"

    def test_missing_visited_urls_key(self):
        results = [
            {"name": "Agent1"},  # no visited_urls key
        ]
        records, text = _collect_citations(results)
        assert records == []
        assert text == ""

    def test_citation_numbers_sequential(self):
        results = [
            {"name": "A", "visited_urls": [f"https://url{i}.com" for i in range(5)]},
        ]
        records, text = _collect_citations(results)
        for i, rec in enumerate(records):
            assert rec["citation_number"] == i + 1
        # Check text format
        lines = text.strip().split("\n")
        assert len(lines) == 5
        assert lines[0] == "[1] https://url0.com"
        assert lines[4] == "[5] https://url4.com"


# ---------------------------------------------------------------------------
# aggregate_node citation integration tests
# ---------------------------------------------------------------------------


class TestAggregateNodeCitations:
    """Test that aggregate_node builds and saves citations."""

    @pytest.mark.asyncio
    async def test_aggregate_node_creates_citations(self):
        """Verify aggregate_node calls CitationRepository.bulk_create."""
        from src.services import research_graph

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_session_factory = MagicMock(return_value=mock_session)

        mock_research = MagicMock()
        mock_research.report_markdown = None
        mock_research.total_tokens = 0
        mock_research.status = "running"
        mock_research.completed_at = None

        mock_repo = MagicMock()
        mock_repo.find_by_id = AsyncMock(return_value=mock_research)

        mock_cit_repo = MagicMock()
        mock_cit_repo.bulk_create = AsyncMock(return_value=[])

        mock_llm = MagicMock()
        mock_llm.aggregate_report = AsyncMock(return_value=("# Report\n[1] findings", 100))

        state = {
            "research_id": uuid4(),
            "topic": "test topic",
            "plan": [{"name": "A", "goal": "g", "searchDirection": "s"}],
            "sub_agent_results": [
                {
                    "name": "Agent1",
                    "status": "completed",
                    "findings": "Some findings",
                    "visited_urls": ["https://example.com/1", "https://example.com/2"],
                    "token_used": 50,
                },
            ],
            "total_tokens": 100,
            "report_markdown": "",
            "cancel_requested": False,
        }

        config = {"configurable": {"db_session_factory": mock_session_factory}}

        with patch.object(research_graph, "ResearchRepository", return_value=mock_repo), \
             patch.object(research_graph, "CitationRepository", return_value=mock_cit_repo), \
             patch.object(research_graph, "_get_llm_service", return_value=mock_llm), \
             patch.object(research_graph.sse_manager, "push_event", new_callable=AsyncMock):

            result = await research_graph.aggregate_node(state, config)

        assert result["status"] == "completed"
        # Verify LLM was called with citation_map
        mock_llm.aggregate_report.assert_called_once()
        call_kwargs = mock_llm.aggregate_report.call_args
        assert "citation_map" in call_kwargs.kwargs
        assert "https://example.com/1" in call_kwargs.kwargs["citation_map"]
        # Verify citations were saved
        mock_cit_repo.bulk_create.assert_called_once()
        records = mock_cit_repo.bulk_create.call_args[0][1]
        assert len(records) == 2


# ---------------------------------------------------------------------------
# CitationRepository tests (unit, with mock DB session)
# ---------------------------------------------------------------------------


class TestCitationRepository:
    """Test CitationRepository with mock session."""

    @pytest.mark.asyncio
    async def test_bulk_create(self):
        from src.repos.citation_repo import CitationRepository

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        repo = CitationRepository(mock_session)
        citations = [
            {"citation_number": 1, "url": "https://a.com", "title": "A", "snippet": "snip", "source_agent": "agent"},
            {"citation_number": 2, "url": "https://b.com", "title": "B", "snippet": "", "source_agent": "agent"},
        ]
        result = await repo.bulk_create(uuid4(), citations)
        assert len(result) == 2
        assert mock_session.add.call_count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_research(self):
        from src.repos.citation_repo import CitationRepository

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = CitationRepository(mock_session)
        result = await repo.find_by_research(uuid4())
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_research(self):
        from src.repos.citation_repo import CitationRepository

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()

        repo = CitationRepository(mock_session)
        await repo.delete_by_research(uuid4())
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()
