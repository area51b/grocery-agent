"""The insight agent: a LangGraph agent over the deterministic analysis tools.

Spec contract (insight-agent capability):
- maps natural-language questions to the analysis tools;
- may chain multiple tool calls for compound questions;
- MUST NOT do arithmetic itself — it relays tool-computed values verbatim and
  declines, without inventing numbers, when no tool can answer;
- has no access to credentials, the browser session, or raw captured data.
"""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from grocery_agent.agent.env import load_env
from grocery_agent.tools import registry as tools

_SYSTEM_PROMPT = """\
You are a family grocery spending assistant. You answer questions about the
household's grocery purchases using the provided analysis tools.

Rules you must always follow:
1. Never perform arithmetic yourself. Every number in your answers must come
   directly from a tool result. Relay tool values verbatim.
2. If no tool can answer the question from stored data, say so plainly. Do
   not estimate, extrapolate, or invent figures.
3. When you present an aggregate figure, state the data coverage (the ingested
   date range and transaction count) that the answer is based on.
4. When a question could be about individual accounts (e.g. "who spent
   more?"), use the per-account tools; otherwise default to household-wide
   figures, which already combine all accounts.
5. You have no access to store credentials or raw browsing data and must not
   pretend otherwise.
6. Prefer the higher-level analysis tools (spend breakdowns, product search,
   price history, top products, transaction listings, period comparison).
   When no higher-level tool fits, use the run_sql tool: write a single
   read-only SELECT against the store's transaction_record and line_item
   tables. run_sql cannot modify data; never attempt to.
7. If run_sql returns an error, fix the query and retry once or twice; if it
   still fails, tell the user the question could not be answered.
"""

DEFAULT_MODEL = "glm-5.3-flash"

_agent = None


def _env(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        raise RuntimeError(f"{key} is not set. Copy .env.example to .env and fill it in.")
    return value


def build_agent():
    """Build the ReAct agent over the deterministic tools (cached)."""
    global _agent
    if _agent is None:
        load_env()
        llm = ChatOpenAI(
            model=os.environ.get("GROCERY_MODEL", DEFAULT_MODEL),
            base_url=_env("GROCERY_GATEWAY_BASE_URL"),
            api_key=_env("GROCERY_GATEWAY_API_KEY"),
            temperature=0,
        )
        _agent = create_react_agent(
            llm,
            [
                tools.spend,
                tools.spend_by_type,
                tools.spend_by_month,
                tools.spend_by_account,
                tools.product_spend,
                tools.promotion_savings,
                tools.promoted_item_details,
                tools.search_products,
                tools.product_price_history,
                tools.top_products,
                tools.transaction_details,
                tools.transaction_items,
                tools.compare_periods,
                tools.run_sql,
            ],
            prompt=_SYSTEM_PROMPT,
        )
    return _agent


def run_ask(question: str) -> int:
    """Answer one question via the agent. Returns a process exit code."""
    agent = build_agent()
    result = agent.invoke({"messages": [("user", question)]})
    print(result["messages"][-1].content)
    return 0
