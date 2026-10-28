import json
import os
from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from procurement.tools import TOOLS, call_tool
from procurement.orchestrator import SYSTEM_PROMPT


class State(TypedDict):
    messages: Annotated[list, add_messages]


def _make_llm(model: str):
    return ChatOpenAI(
        model=model,
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
        temperature=0.2,
        timeout=90,
        max_retries=4,  # retries 429/503 with backoff
    ).bind_tools(TOOLS)


# Main model from NVIDIA_MODEL. Optional comma-separated backups in
# NVIDIA_FALLBACK_MODELS are tried if the main one keeps failing.
_primary = _make_llm(os.environ["NVIDIA_MODEL"])
_fallbacks = [
    _make_llm(m.strip())
    for m in os.environ.get("NVIDIA_FALLBACK_MODELS", "").split(",")
    if m.strip()
]
llm = _primary.with_fallbacks(_fallbacks) if _fallbacks else _primary


def agent(state: State) -> dict:
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
    return {"messages": [response]}


def run_tools(state: State) -> dict:
    last = state["messages"][-1]
    outputs = []
    for tc in last.tool_calls:
        result = call_tool(tc["name"], tc["args"])
        outputs.append(
            ToolMessage(content=json.dumps(result, default=str), tool_call_id=tc["id"])
        )
    return {"messages": outputs}


def route(state: State) -> str:
    return "tools" if state["messages"][-1].tool_calls else END


builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", run_tools)
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route, ["tools", END])
builder.add_edge("tools", "agent")

graph = builder.compile()
