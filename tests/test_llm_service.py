import json
import pytest
from unittest.mock import AsyncMock, patch
from src.services import llm_service
from src.services.prompts import (
    PLAN_GENERATION_PROMPT,
    PLAN_REVISION_PROMPT,
    SUB_AGENT_SEARCH_PROMPT,
    AGGREGATE_PROMPT,
)


class TestPrompts:
    def test_plan_generation_template_formatted(self):
        prompt = PLAN_GENERATION_PROMPT.format(topic="AI 安全", template="tech_research")
        assert "AI 安全" in prompt
        assert "tech_research" in prompt
        assert "tech_research" in prompt

    def test_plan_revision_template_formatted(self):
        prompt = PLAN_REVISION_PROMPT.format(
            topic="AI 安全",
            current_plan='[{"name":"test"}]',
            feedback="请增加对比维度",
        )
        assert "AI 安全" in prompt
        assert "请增加对比维度" in prompt

    def test_sub_agent_search_template_formatted(self):
        prompt = SUB_AGENT_SEARCH_PROMPT.format(
            topic="研究主题",
            findings="无",
            search_results="结果1",
            direction="搜索方向",
        )
        assert "研究主题" in prompt
        assert "结果1" in prompt
        assert "搜索方向" in prompt

    def test_aggregate_template_formatted(self):
        prompt = AGGREGATE_PROMPT.format(
            topic="AI 安全",
            plan="[]",
            sub_agent_findings="发现文本",
            citation_map="[1] https://example.com",
        )
        assert "AI 安全" in prompt
        assert "发现文本" in prompt
        assert "[1] https://example.com" in prompt


class TestJsonParsing:
    def test_extract_clean_json_list(self):
        text = '[{"name": "A", "goal": "G", "searchDirection": "D"}]'
        result = llm_service._extract_json_block(text)
        assert isinstance(result, list)
        assert result[0]["name"] == "A"

    def test_extract_clean_json_object(self):
        text = '{"findings": "F", "sufficient": true}'
        result = llm_service._extract_json_block(text)
        assert isinstance(result, dict)
        assert result["findings"] == "F"
        assert result["sufficient"] is True

    def test_extract_json_in_codeblock(self):
        text = '```json\n[{"name": "B"}]\n```'
        result = llm_service._extract_json_block(text)
        assert isinstance(result, list)
        assert result[0]["name"] == "B"

    def test_extract_json_buried_in_text(self):
        text = 'Some text [{"name": "C"}] more text'
        result = llm_service._extract_json_block(text)
        assert isinstance(result, list)
        assert result[0]["name"] == "C"

    def test_extract_json_invalid_returns_none(self):
        text = "Not valid JSON at all"
        result = llm_service._extract_json_block(text)
        assert result is None


MOCK_RESPONSE = type("Response", (), {
    "choices": [type("Choice", (), {
        "message": type("Message", (), {"content": '{"result": "ok"}'})()
    })()],
    "usage": type("Usage", (), {
        "dict": lambda self=None: {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    })(),
})()


class TestLlmService:
    def make_plan_response(self, count=3):
        agents = [
            {"name": f"子课题{i+1}", "goal": f"目标{i+1}", "searchDirection": f"搜索方向{i+1}"}
            for i in range(count)
        ]
        return json.dumps(agents)

    @pytest.mark.asyncio
    async def test_generate_plan_parses_list(self):
        plan_json = self.make_plan_response(3)
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": plan_json})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            plan, tokens = await llm_service.generate_plan("测试", "custom")
            assert len(plan) == 3
            assert plan[0]["name"] == "子课题1"
            assert tokens == 150

    @pytest.mark.asyncio
    async def test_generate_plan_fallback_on_invalid_json(self):
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": "Sorry, I can't help"})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            plan, tokens = await llm_service.generate_plan("测试", "custom")
            assert len(plan) == 1
            assert "测试" in plan[0]["goal"]
            assert tokens == 15

    @pytest.mark.asyncio
    async def test_revise_plan_returns_updated(self):
        new_plan_json = json.dumps([
            {"name": "新课题", "goal": "新目标", "searchDirection": "新方向"}
        ])
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": new_plan_json})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            plan, tokens = await llm_service.revise_plan("测试", [{"name": "旧"}], "请修改")
            assert len(plan) == 1
            assert plan[0]["name"] == "新课题"
            assert tokens == 150

    @pytest.mark.asyncio
    async def test_revise_plan_fallback_returns_original(self):
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": "invalid"})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            })(),
        })()

        original = [{"name": "原始"}]
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            plan, tokens = await llm_service.revise_plan("测试", original, "请修改")
            assert plan is original
            assert tokens == 15

    @pytest.mark.asyncio
    async def test_sub_agent_search_parses_result(self):
        findings_json = json.dumps({
            "findings": "## 发现\n内容",
            "sufficient": True,
            "new_keywords": "",
        })
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": findings_json})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            result, tokens = await llm_service.sub_agent_search("旧发现", "新结果", "方向")
            assert result["sufficient"] is True
            assert "发现" in result["findings"]
            assert tokens == 150

    @pytest.mark.asyncio
    async def test_sub_agent_search_fallback(self):
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": "nonsense"})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            result, tokens = await llm_service.sub_agent_search("旧发现", "新结果", "方向")
            assert result["sufficient"] is True
            assert "新结果" in result["findings"]
            assert tokens == 15

    @pytest.mark.asyncio
    async def test_aggregate_report_returns_markdown(self):
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": "# 报告\n\n内容"})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            report, tokens = await llm_service.aggregate_report("测试", [], "发现")
            assert "# 报告" in report
            assert tokens == 300

    @pytest.mark.asyncio
    async def test_aggregate_report_truncates_long_content(self):
        long_content = "# " + "x" * 60000
        mock_resp = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": long_content})()
            })()],
            "usage": type("Usage", (), {
                "dict": lambda self=None: {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}
            })(),
        })()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            report, tokens = await llm_service.aggregate_report("测试", [], "发现")
            assert len(report) <= 50000
            assert tokens == 300
