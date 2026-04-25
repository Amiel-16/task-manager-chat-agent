# AI Task Manager Agent

A production-ready Python service that provides a natural language chat interface for task management.  
It uses **FastAPI** for the API layer, **LangGraph** for orchestration, and **MCP** to expose task tools cleanly.

## Features

- `POST /chat` endpoint for natural language task management
- LangGraph workflow with modular nodes:
  - Input node
  - Decision node (LLM)
  - Tool node
  - Response node
- HTTP tools that call an existing backend API at `http://backend:8000` (Docker network) or `http://localhost:8000` (local)
- MCP server with registered task tools
- Typed, modular code with clear separation of concerns

## Project Structure

```text
ai-agent/
  app/
    main.py
    agent/
      graph.py
      nodes.py
      state.py
    tools/
      tasks.py
    mcp/
      server.py
    schemas/
      chat.py
    core/
      config.py
  requirements.txt
  README.md
```

## Architecture

1. Client sends message to `POST /chat`
2. FastAPI calls `run_agent()`
3. LangGraph routes request:
   - LLM decides action
   - Tool node executes MCP-backed tool logic when needed
   - Response node formats final answer
4. Tools call backend task endpoints via `httpx`

- **Persistence & Memory**: Integrated `MemorySaver` checkpointer to maintain conversation state across multiple turns.
- **Thread Management**: Supports `thread_id` in the `run_agent` function to isolate and resume unique user sessions.
- **Stateful Workflows**: Automatic checkpointing of the `AgentState` after every node execution for reliability.

## Prerequisites

- Python 3.11+
- Existing backend API running on `http://localhost:8000`
- OpenAI-compatible LLM credentials

## Setup

```bash
cd ai-agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in `ai-agent/`:

```env
GEMINI_API_KEY=your_api_key
MODEL_NAME=gemini-2.5-flash
BACKEND_BASE_URL=http://backend:8000
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

Health check:

```bash
curl http://localhost:9000/health
```

## Run With Docker

```bash
docker-compose up --build
```

## Available Services

- Backend: `http://localhost:8000`
- AI Agent: `http://localhost:8001`

## Chat API

### Endpoint

- `POST /chat`

### Request

```json
{
  "message": "I need to study React tomorrow"
}
```

### Response

```json
{
  "response": "Task created successfully."
}
```

## Example Prompts

- `I need to study React tomorrow`
- `What are my tasks?`
- `Rename task 1 to study FastAPI`
- `Delete task 2`
- `What should I work on today?`

## Notes

- This service acts as an AI layer on top of the backend task API.
- Tool failures return user-friendly error messages instead of raw exceptions.
