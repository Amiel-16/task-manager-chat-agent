from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class BackendAPIError(Exception):
    pass


async def _request(method: str, path: str, token: str = "", json_body: dict[str, Any] | None = None) -> Any:
    url = f"{settings.backend_base_url}{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.request(method=method, url=url, json=json_body, headers=headers)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {"status": "ok"}
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or exc.response.reason_phrase
        raise BackendAPIError(f"Backend request failed with status {exc.response.status_code}: {detail}") from exc
    except httpx.RequestError as exc:
        raise BackendAPIError(f"Unable to connect to backend API at {settings.backend_base_url}.") from exc


async def create_task(text: str, token: str = "") -> dict[str, Any]:
    if not text.strip():
        raise BackendAPIError("Task text cannot be empty.")
    payload = {"text": text.strip(), "done": False}
    data = await _request("POST", "/tasks", token=token, json_body=payload)
    return {"message": "Task created successfully.", "task": data}


async def get_tasks(token: str = "") -> dict[str, Any]:
    data = await _request("GET", "/tasks", token=token)
    tasks: list[dict[str, Any]] = data if isinstance(data, list) else data.get("tasks", [])
    return {"count": len(tasks), "tasks": tasks}


async def update_task(
    task_id: int,
    token: str = "",
    text: str | None = None,
    done: bool | None = None,
) -> dict[str, Any]:
    if task_id <= 0:
        raise BackendAPIError("task_id must be a positive integer.")
    if text is None and done is None:
        raise BackendAPIError("Provide text and/or done to update a task.")
    payload: dict[str, Any] = {}
    if text is not None:
        if not text.strip():
            raise BackendAPIError("Task text cannot be empty.")
        payload["text"] = text.strip()
    if done is not None:
        payload["done"] = done
    if not payload:
        raise BackendAPIError("Provide text and/or done to update a task.")
    data = await _request("PUT", f"/tasks/{task_id}", token=token, json_body=payload)
    return {"message": f"Task {task_id} updated successfully.", "task": data}


async def delete_task(task_id: int, token: str = "") -> dict[str, Any]:
    if task_id <= 0:
        raise BackendAPIError("task_id must be a positive integer.")
    data = await _request("DELETE", f"/tasks/{task_id}", token=token)
    return {"message": f"Task {task_id} deleted successfully.", "result": data}

# TODO: add get task id 
