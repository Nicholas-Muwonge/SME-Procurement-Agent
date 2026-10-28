import json
import os
from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from procurement.tools import TOOLS, call_tool
from procurement.orchestrator import SYSTEM_PROMPT
from pathlib import Path

class State(TypedDict):
    messages: Annotated[list, add_messages]


# NVIDIA's hosted catalog is OpenAI-compatible. Pick any model that passed
# the tool-calling test and set NVIDIA_MODEL in .env to override the default.
llm = ChatOpenAI(
    model=os.environ.get("NVIDIA_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1.5"),
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    temperature=0.2,
).bind_tools(TOOLS)


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


p = Path("src/procurement/graph.py")
t = p.read_text()
if "timeout=" not in t:
    t = t.replace("    temperature=0.2,\n).bind_tools(TOOLS)",
                  "    temperature=0.2,\n    timeout=60,\n    max_retries=1,\n).bind_tools(TOOLS)", 1)
    p.write_text(t)
    print("timeout added")
else:
    print("already has a timeout")

builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", run_tools)
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route, ["tools", END])
builder.add_edge("tools", "agent")

graph = builder.compile()
