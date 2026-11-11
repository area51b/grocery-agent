"""Tests for agent tool registration (task 4.1)."""

from __future__ import annotations

import pytest

from grocery_agent import agent as agent_module
from grocery_agent.tools import registry


@pytest.fixture
def fresh_agent(monkeypatch):
    """Env vars for construction and a clean agent cache around the test."""
    monkeypatch.setenv("GROCERY_GATEWAY_BASE_URL", "http://localhost:9999")
    monkeypatch.setenv("GROCERY_GATEWAY_API_KEY", "test-key")
    monkeypatch.setenv("GROCERY_MODEL", "test-model")
    saved = agent_module._agent
    agent_module._agent = None
    yield
    agent_module._agent = saved


EXPECTED_TOOLS = {
    "spend",
    "spend_by_type",
    "spend_by_month",
    "spend_by_account",
    "product_spend",
    "promotion_savings",
    "promoted_item_details",
    "search_products",
    "product_price_history",
    "top_products",
    "transaction_details",
    "transaction_items",
    "compare_periods",
    "run_sql",
}


class TestAgentToolRegistration:
    def test_build_agent_binds_every_registry_tool(self, fresh_agent):
        agent = agent_module.build_agent()
        tool_node = agent.nodes["tools"].bound
        bound_names = set(tool_node.tools_by_name)
        assert bound_names == EXPECTED_TOOLS

    def test_run_sql_is_registered(self, fresh_agent):
        agent = agent_module.build_agent()
        bound_names = set(agent.nodes["tools"].bound.tools_by_name)
        assert "run_sql" in bound_names

    def test_registry_exposes_all_tools(self):
        for name in EXPECTED_TOOLS:
            assert callable(getattr(registry, name))


class _StubReply:
    def __init__(self, content):
        self.content = content


class StubAgent:
    """Stands in for the LangGraph agent; records questions, returns fixed text."""

    def __init__(self):
        self.questions = []

    async def ainvoke(self, inputs):
        self.questions.append(inputs["messages"][0][1])
        return {"messages": [("user", self.questions[-1]), _StubReply("stub answer")]}


class TestAnswerQuestion:
    @pytest.mark.asyncio
    async def test_answer_question_returns_final_message_text(self, monkeypatch):
        stub = StubAgent()
        monkeypatch.setattr(agent_module, "_agent", stub)

        reply = await agent_module.answer_question("How much did we spend?")

        assert reply == "stub answer"
        assert stub.questions == ["How much did we spend?"]
