"""Graph construction (SPEC §8, §24).

Two separate graphs, both deterministic and linear:

    challenge:  START -> load_context -> generate_challenge -> END
    discovery:  START -> load_challenge -> analyze_photo -> evaluate_discovery ->
                generate_feedback -> save_discovery -> update_profile -> END

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


def build_discovery_graph(  # noqa: C901
    *,
    service: Any = None,
    load_challenge: Callable[[str, str], dict[str, Any] | None] | None = None,
    save_discovery: Callable[..., dict[str, Any]] | None = None,
    refresh_profile: Callable[[str], dict[str, Any]] | None = None,
    pipeline: str | None = None,
    image_bytes: bytes = b"",
    image_mime_type: str = "image/jpeg",
):
    """START -> load_challenge -> analyze_photo -> evaluate_discovery ->
    generate_feedback -> save_discovery -> update_profile -> END.

    Linear by design (SPEC §8). Even in the combined pipeline, `evaluate_discovery`
    stays in the graph so the two pipelines share one shape.

    The raw image bytes are bound into the node closure rather than stored in
    state, because the state must stay serializable (SPEC §9).
    """
    mode = pipeline or nodes.DISCOVERY_PIPELINE

    async def _load_challenge(state: DiscoveryState) -> dict[str, Any]:
        return nodes.load_challenge(state, load=load_challenge)

    async def _analyze_photo(state: DiscoveryState) -> dict[str, Any]:
        payload = {
            **state,
            "image_bytes": image_bytes,
            "image_mime_type": image_mime_type,
        }
        return nodes.analyze_photo(payload, service=service, pipeline=mode)

    async def _evaluate(state: DiscoveryState) -> dict[str, Any]:
        return nodes.evaluate_discovery(state, service=service, pipeline=mode)

    async def _feedback(state: DiscoveryState) -> dict[str, Any]:
        return nodes.generate_feedback(state, service=service)

    async def _save(state: DiscoveryState) -> dict[str, Any]:
        return nodes.save_discovery(state, save=save_discovery)

    async def _profile(state: DiscoveryState) -> dict[str, Any]:
        return nodes.update_profile(state, refresh=refresh_profile)

    builder = StateGraph(DiscoveryState)
    builder.add_node("load_challenge", _load_challenge)
    builder.add_node("analyze_photo", _analyze_photo)
    builder.add_node("evaluate_discovery", _evaluate)
    builder.add_node("generate_feedback", _feedback)
    builder.add_node("save_discovery", _save)
    builder.add_node("update_profile", _profile)

    def _route_after_load(state: DiscoveryState) -> str:
        """Never call the model when there is no challenge to judge against."""
        return "skip" if state.get("error") else "analyze_photo"

    builder.add_edge(START, "load_challenge")
    builder.add_conditional_edges(
        "load_challenge",
        _route_after_load,
        {"analyze_photo": "analyze_photo", "skip": END},
    )
    builder.add_edge("analyze_photo", "evaluate_discovery")
    builder.add_edge("evaluate_discovery", "generate_feedback")
    builder.add_edge("generate_feedback", "save_discovery")
    builder.add_edge("save_discovery", "update_profile")
    builder.add_edge("update_profile", END)
    return builder.compile()


async def run_discovery_graph(
    user_id: str,
    *,
    challenge_id: str,
    image_bytes: bytes,
    image_mime_type: str,
    image_path: str = "",
    **kwargs: Any,
) -> DiscoveryState:
    """Run the discovery graph, capturing model errors into `state["error"]`."""
    graph = build_discovery_graph(
        image_bytes=image_bytes, image_mime_type=image_mime_type, **kwargs
    )
    state: DiscoveryState = {
        "user_id": user_id,
        "challenge_id": challenge_id,
        "image_mime_type": image_mime_type,
        "image_path": image_path,
    }
    try:
        return await graph.ainvoke(state)
    except GemmaError as exc:
        logger.warning("Discovery graph failed for user %s: %s", user_id, exc.detail or exc.message)
        return {**state, "error": exc.message}


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
