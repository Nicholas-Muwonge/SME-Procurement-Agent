import os
import json
from typing import Annotated, TypedDict
from dotenv import load_dotenv

load_dotenv()

from procurement.graph import graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

graph = builder.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "test-req-002"}}

user_input = {
    "messages": [("user", "Check ITM-001. If below reorder point, create a draft requisition for 50 units. Requested by Nicholas.")]
}

print("--- Starting Graph ---")
for event in graph.stream(user_input, config, stream_mode="values"):
    if "messages" in event:
        event["messages"][-1].pretty_print()

# Check if the graph actually paused for approval
state = graph.get_state(config)

# A paused graph will have a 'next' attribute indicating where it's waiting
if state.next and "approval_gate" in state.next:
    print("\n--- Graph Paused for Human Approval ---")
    last_message = state.values['messages'][-1]
    
    # Safely get the tool call
    if last_message.tool_calls:
        print(f"Waiting for approval to create: {last_message.tool_calls[0]['args']}")
    
    # Simulate human approval
    print("\n--- Resuming with Human Approval ---")
    for event in graph.stream(Command(resume="approve"), config, stream_mode="values"):
        if "messages" in event:
            event["messages"][-1].pretty_print()
else:
    print("\n--- Graph Finished (No approval was needed) ---")