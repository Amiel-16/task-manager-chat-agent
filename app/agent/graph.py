from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import decision_node, input_node, response_node, tool_node
from app.agent.state import AgentState


def _route_after_decision(state: AgentState) -> str:
    action = state.get("action", "direct_response")
    if action == "direct_response":
        return "response"
    return "tool"


def build_graph():
    checkpointer = MemorySaver()
    graph = StateGraph(AgentState)
    graph.add_node("input", input_node)
    graph.add_node("decision", decision_node)
    graph.add_node("tool", tool_node)
    graph.add_node("response", response_node)

    graph.add_edge(START, "input")
    graph.add_edge("input", "decision")
    graph.add_conditional_edges("decision", _route_after_decision, {"tool": "tool", "response": "response"})
    graph.add_edge("tool", "decision")
    graph.add_edge("response", END)

    return graph.compile(checkpointer=checkpointer)


agent_graph = build_graph()


async def run_agent(message: str, token: str = "", thread_id: str | None = None) -> str:
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    result = await agent_graph.ainvoke({"user_message": message, "token": token}, config=config)
    return result.get("final_response", "I could not generate a response.")
