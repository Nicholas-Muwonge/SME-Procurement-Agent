import json
import os
from dotenv import load_dotenv

load_dotenv()

from typing import Annotated, TypedDict
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from procurement.tools import TOOLS, call_tool
from procurement.orchestrator import SYSTEM_PROMPT

class State(TypedDict):
    messages: Annotated[list, add_messages]
    approval_status: str

def _make_llm(model: str):
    return ChatOpenAI(
        model=model,
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
        temperature=0.2,
        timeout=90,
        max_retries=4,
    ).bind_tools(TOOLS)

_primary = _make_llm(os.environ["NVIDIA_MODEL"])
_fallbacks = [
    _make_llm(m.strip())
    for m in os.environ.get("NVIDIA_FALLBACK_MODELS", "").split(",")
    if m.strip()
]
llm = _primary.with_fallbacks(_fallbacks) if _fallbacks else _primary

def agent(state: State) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def approval_gate(state: State) -> dict:
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    req_data = tool_call["args"]

    human_decision = interrupt({
        "action": "create_draft_requisition",
        "details": req_data,
        "message": "A draft requisition is ready. Approve or Reject?"
    })

    if human_decision == "approve":
        return {"approval_status": "approved"}
    else:
        return {
            "approval_status": "rejected",
            "messages": [ToolMessage(content="Requisition rejected by human.", tool_call_id=tool_call["id"])]
        }

def run_tools(state: State) -> dict:
    last = state["messages"][-1]
    outputs = []
    for tc in last.tool_calls:
        if tc["name"] == "create_draft_requisition":
            if state.get("approval_status") != "approved":
                outputs.append(ToolMessage(content="Error: Requisition must be approved by human first.", tool_call_id=tc["id"]))
                continue
                
        result = call_tool(tc["name"], tc["args"])
        outputs.append(
            ToolMessage(content=json.dumps(result, default=str), tool_call_id=tc["id"])
        )
    
    return {"messages": outputs, "approval_status": "none"}

# --- Routing Logic ---

def route_agent(state: State) -> str:
    last_message = state["messages"][-1]
    
    if not last_message.tool_calls:
        return END
        
    for tc in last_message.tool_calls:
        if tc["name"] == "create_draft_requisition":
            if state.get("approval_status") != "approved":
                return "approval_gate"
                
    return "tools"

def route_approval(state: State) -> str:
    # If approved, execute the tool directly. If rejected, return to the agent.
    if state.get("approval_status") == "approved":
        return "tools"
    return "agent"

# --- Build Graph ---
builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", run_tools)
builder.add_node("approval_gate", approval_gate)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_agent, ["tools", "approval_gate", END])

# Conditional edge from approval_gate based on the human decision
builder.add_conditional_edges("approval_gate", route_approval, ["tools", "agent"])

builder.add_edge("tools", "agent")

graph = builder.compile()