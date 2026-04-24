from __future__ import annotations

from typing import Any, Literal, TypedDict


ActionName = Literal["create_task", "get_tasks", "update_task", "delete_task", "recommend_today", "direct_response"]


class AgentState(TypedDict, total=False):
    """Graph state. tool_result is the latest MCP payload; tool_results_history lists prior hops in one user turn."""

    user_message: str
    token: str
    action: ActionName
    action_args: dict[str, Any]
    tool_result: dict[str, Any]
    final_response: str
    tool_results_history: list[dict[str, Any]]
