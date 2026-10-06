"""Graph construction (SPEC §8, §24).

Two separate graphs, both deterministic and linear:

    challenge:  START -> load_context -> generate_challenge -> END
    discovery:  built in Phase 4

There is no autonomous loop and no conditional branching; each node runs once.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.errors import GemmaError
from app.graph import nodes
from app.graph.state import DiscoveryState

logger = logging.getLogger(__name__)


def build_challenge_graph(
    *,
    service: Any = None,
    load_profile: Callable[[str], dict[str, Any]] | None = None,
    load_history: Callable[[str], list[str]] | None = None,
    load_discoveries: Callable[[str], list[str]] | None = None,
):
    """START -> load_context -> generate_challenge -> END."""

    async def _load_context(state: DiscoveryState) -> dict[str, Any]:
        return nodes.load_context(
            state,
            load_profile=load_profile,
            load_history=load_history,
            load_discoveries=load_discoveries,
        )

    async def _generate_challenge(state: DiscoveryState) -> dict[str, Any]:
        return nodes.generate_challenge(state, service=service)

    builder = StateGraph(DiscoveryState)
    builder.add_node("load_context", _load_context)
    builder.add_node("generate_challenge", _generate_challenge)
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "generate_challenge")
    builder.add_edge("generate_challenge", END)
    return builder.compile()


async def run_challenge_graph(user_id: str, **kwargs: Any) -> DiscoveryState:
    """Run the challenge graph, converting model errors into `state["error"]`.

    The caller decides how to surface the failure; the graph never raises raw
    provider exceptions (SPEC §26).
    """
    graph = build_challenge_graph(**kwargs)
    state: DiscoveryState = {"user_id": user_id}
    try:
        return await graph.ainvoke(state)
    except GemmaError as exc:
        logger.warning("Challenge graph failed for user %s: %s", user_id, exc.detail or exc.message)
        return {**state, "error": exc.message}
