"""
Orchestrator with Function Calling + Structured Logging
SME Procurement-Preparation Agent – Week 4
"""

import json
import os
from datetime import datetime
from openai import OpenAI
from tools import TOOLS, call_tool

client = OpenAI()

LOG_DIR = "evidence/traces"
os.makedirs(LOG_DIR, exist_ok=True)

def save_trace(trace: dict):
    """Save a complete execution trace to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{LOG_DIR}/trace_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, default=str)
    print(f"\n[TRACE SAVED] → {filename}")
    return filename


SYSTEM_PROMPT = """You are a careful and reliable Procurement Assistant Agent for a Ugandan Small or Medium Enterprise (SME).

Your primary goal is:
Given a user request about an inventory item, you must:
1. Check the current inventory status using the available tools.
2. Decide whether a reorder is required.
3. If a reorder is required, retrieve supplier quotations.
4. Create a draft purchase requisition.
5. Stop and clearly hand over to a human for approval.

### Allowed Tools
You may only use these tools:
- get_inventory
- get_quotations
- create_draft_requisition

You must never attempt to:
- Approve a requisition
- Change status to “Approved”
- Place an order
- Select a final supplier
- Commit funds or make payments

### Behaviour Rules
- Always use tools to obtain current data. Never invent stock levels, prices, or quotations.
- After creating a draft requisition, you must stop and tell the user that the draft is waiting for human approval.
- If the item does not need reordering, clearly say so and stop.
- If you encounter missing data, invalid item IDs, or repeated tool errors, stop and hand over to the human.
- Keep your responses concise, professional, and transparent.

You are a bounded agent. You prepare work and make safe recommendations, but final decisions always remain with the human.
"""

def run_agent(user_message: str, max_turns: int = 6) -> str:
    """
    Function-calling loop with full observability logging.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    trace = {
        "timestamp_start": datetime.now().isoformat(),
        "user_message": user_message,
        "model": "gpt-4o-mini",
        "turns": [],
        "final_answer": None,
        "status": "running"
    }

    print("\n" + "="*70)
    print(f"USER: {user_message}")
    print("="*70)

    for turn_number in range(1, max_turns + 1):
        turn_data = {
            "turn": turn_number,
            "timestamp": datetime.now().isoformat(),
            "tool_calls": [],
            "assistant_message": None
        }

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2
        )

        msg = response.choices[0].message
        messages.append(msg)

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                print(f"\n→ [{turn_number}] Calling tool: {tool_name}")
                print(f"  Arguments: {arguments}")

                start_time = datetime.now()
                tool_result = call_tool(tool_name, arguments)
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                print(f"  Result: {json.dumps(tool_result, indent=2)}")

                tool_call_record = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": tool_result,
                    "duration_ms": round(duration_ms, 2),
                    "success": "error" not in tool_result
                }
                turn_data["tool_calls"].append(tool_call_record)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })

            trace["turns"].append(turn_data)

        else:
            final_answer = msg.content
            turn_data["assistant_message"] = final_answer
            trace["turns"].append(turn_data)

            trace["final_answer"] = final_answer
            trace["status"] = "completed"
            trace["timestamp_end"] = datetime.now().isoformat()

            print("\nASSISTANT:")
            print(final_answer)

            save_trace(trace)
            return final_answer

    # Safety stop
    trace["status"] = "max_turns_reached"
    trace["timestamp_end"] = datetime.now().isoformat()
    save_trace(trace)
    return "Maximum turns reached. Please try a simpler request."

if __name__ == "__main__":
    run_agent(
        "Check the current stock of ITM-001 (Cement). "
        "If it is below the reorder point, create a draft requisition "
        "using the recommended quantity. "
        "Justification: Stock below reorder point. "
        "Requested by: Nicholas"
    )