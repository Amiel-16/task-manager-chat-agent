from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.tools.tasks import create_task, delete_task, get_tasks, update_task


mcp = FastMCP("task-manager-mcp")

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]

_TOOL_REGISTRY: dict[str, ToolHandler] = {
    "create_task": create_task,
    "get_tasks": get_tasks,
    "update_task": update_task,
    "delete_task": delete_task,
}


@mcp.tool()
async def create_task_tool(text: str) -> dict[str, Any]:
    return await create_task(text=text)


@mcp.tool()
async def get_tasks_tool() -> dict[str, Any]:
    return await get_tasks()


@mcp.tool()
async def update_task_tool(task_id: int, text: str | None = None, done: bool | None = None) -> dict[str, Any]:
    return await update_task(task_id=task_id, text=text, done=done)


@mcp.tool()
async def delete_task_tool(task_id: int) -> dict[str, Any]:
    return await delete_task(task_id=task_id)


def get_tool_registry() -> dict[str, ToolHandler]:
    return dict(_TOOL_REGISTRY)


async def invoke_tool(tool_name: str, args: dict[str, Any], token: str = "") -> dict[str, Any]:
    handler = _TOOL_REGISTRY.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return await handler(**args, token=token)
