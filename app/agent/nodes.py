from __future__ import annotations

import json
from typing import Any, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.agent.state import AgentState
from app.core.config import settings
from app.mcp.server import invoke_tool
from app.tools.tasks import BackendAPIError


SYSTEM_PROMPT = """
You are a task management assistant.
You help users create, list, update, and delete tasks.
You can call tools to perform task operations.
Prefer calling tools when the user asks about task changes or task retrieval.
If user asks "what should I work on today", choose recommend_today.

Mandatory resolution protocol:
If a task ID is missing, call get_tasks immediately. Once the tool returns the list, find the matching ID
and proceed with the update_task or delete_task action in the next step without asking the user for confirmation.

User-facing guidelines:
When listing tasks for the user, NEVER show the task_id or any technical database IDs.
Use bullet points and only show the description and the status (done/not done).
The IDs are for your internal use only to perform actions. Keep them invisible in your final responses."

""".strip()


class DecisionOutput(BaseModel):
    action: Literal["create_task", "get_tasks", "update_task", "delete_task", "recommend_today", "direct_response"]
    action_args: dict[str, Any] = Field(default_factory=dict)
    direct_response: str = ""


def _format_task_status(done: bool) -> str:
    return "(done)" if done else "(not done)"


def _format_task_line(task: dict[str, Any]) -> str:
    text = (task.get("text") or "").strip()
    line_text = text if text else "—"
    return f"- {line_text} {_format_task_status(bool(task.get('done', False)))}"


def _llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.model_name,
        google_api_key=settings.gemini_api_key or None,
        temperature=0,
    )


async def input_node(state: AgentState) -> AgentState:
    # Fresh user turn: drop stale tool data so the model is not confused by prior checkpoints.
    return {
        "user_message": state["user_message"],
        "token": state.get("token", ""),
        "action_args": {},
        "tool_result": {},
        "tool_results_history": [],
        "final_response": "",
    }


def _append_tool_history(state: AgentState, entry: dict[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("tool_results_history") or []) + [entry]


def _serialize_for_prompt(data: Any, max_chars: int = 12000) -> str:
    raw = json.dumps(data, indent=2, default=str)
    if len(raw) > max_chars:
        return raw[:max_chars] + "\n... (truncated)"
    return raw


async def decision_node(state: AgentState) -> AgentState:
    llm = _llm().with_structured_output(DecisionOutput)
    tool_context = ""
    history = state.get("tool_results_history") or []
    if history:
        tool_context = (
            "\n\n--- TOOL OUTPUT HISTORY (newest last; use task id fields from get_tasks) ---\n"
            f"{_serialize_for_prompt(history)}\n"
        )
    elif state.get("tool_result"):
        tool_context = (
            "\n\n--- LAST TOOL OUTPUT ---\n"
            f"{_serialize_for_prompt(state['tool_result'])}\n"
        )
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"

        "--- MANDATORY OPERATING RULES ---\n"

        "1. NEVER ask the user for a task_id. If you don't have it, your ONLY option is to call 'get_tasks' immediately.\n"
        "2. If the user message contains a description (e.g., 'buy food') and the tool output below contains the task list, "
        "you MUST perform the update/delete action using the ID from that list.\n"
        "3. Do not stop after listing tasks when the user asked to update or delete: use the list to find the ID, then "
        "CALL update_task or delete_task in this same turn.\n"
        "4. If get_tasks already ran and the matching task appears in the tool output below, choose update_task or "
        "delete_task NOW—do not ask the user to confirm.\n"
        "5. If the user only asked to list or show tasks and get_tasks output is below, answer with direct_response "
        "and summarize the tasks clearly (include id if present in the JSON).\n\n"

        "--- AVAILABLE ACTIONS ---\n"

        "Return an action and action_args based on the user request.\n"
        "For create_task use {'text': str} for the task description.\n"
        "For get_tasks use {}.\n"
        "For update_task use {'task_id': int, 'text': str?} and/or {'done': bool?}; you may set both.\n"
        "For delete_task use {'task_id': int}.\n"
        "For recommend_today use {}.\n"
        "For direct_response provide direct_response text.\n\n"
        f"User message: {state['user_message']}"
        f"{tool_context}"
    )
    result = await llm.ainvoke(prompt)
    return {
        "action": result.action,
        "action_args": result.action_args,
        "final_response": result.direct_response,
    }


async def tool_node(state: AgentState) -> AgentState:
    action = state.get("action", "direct_response")
    if action == "direct_response":
        return {}

    if action == "recommend_today":
        try:
            tasks_result = await invoke_tool("get_tasks", {}, token=state.get("token", ""))
        except BackendAPIError as exc:
            err = {"error": str(exc)}
            return {"tool_result": err, "tool_results_history": _append_tool_history(state, err)}
        tasks = tasks_result.get("tasks", [])
        if not tasks:
            payload = {
                "recommendation": "You have no tasks. Create one high-impact task to start your day.",
            }
            return {"tool_result": payload, "tool_results_history": _append_tool_history(state, payload)}
        first_task = tasks[0]
        top_text = (first_task.get("text") or "").strip() or "your top task"
        payload = {
            "recommendation": (
                f"Start with '{top_text}'. Focus on completing it first, then review remaining tasks."
            ),
            "tasks": tasks,
        }
        return {"tool_result": payload, "tool_results_history": _append_tool_history(state, payload)}

    try:
        result = await invoke_tool(action, state.get("action_args", {}), token=state.get("token", ""))
        tagged = {"action": action, "result": result}
        return {"tool_result": result, "tool_results_history": _append_tool_history(state, tagged)}
    except BackendAPIError as exc:
        err = {"error": str(exc)}
        tagged = {"action": action, "result": err}
        return {"tool_result": err, "tool_results_history": _append_tool_history(state, tagged)}
    except TypeError as exc:
        err = {"error": f"Invalid tool arguments: {exc}"}
        tagged = {"action": action, "result": err}
        return {"tool_result": err, "tool_results_history": _append_tool_history(state, tagged)}


async def response_node(state: AgentState) -> AgentState:
    if state.get("action") == "direct_response":
        text = state.get("final_response") or "How can I help with your tasks today?"
        return {"final_response": text}

    result = state.get("tool_result", {})
    if "error" in result:
        return {"final_response": f"I could not complete that request: {result['error']}"}

    action = state.get("action")
    if action == "get_tasks":
        tasks = result.get("tasks", [])
        if not tasks:
            return {"final_response": "You currently have no tasks."}
        lines = [_format_task_line(t) for t in tasks if isinstance(t, dict)]
        if not lines:
            return {"final_response": "You currently have no tasks."}
        return {"final_response": "Here are your tasks:\n" + "\n".join(lines)}

    if action == "recommend_today":
        return {"final_response": result.get("recommendation", "Start with your highest-priority open task.")}

    message = result.get("message", "Done.")
    return {"final_response": message}
