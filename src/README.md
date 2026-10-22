
# What this orchestrator does

Sends the user message + system prompt to the model
Lets the model decide which tool(s) to call
Executes the real Python functions (get_inventory, get_quotations, create_draft_requisition)
Feeds the tool results back to the model
Continues until the model produces a final natural-language answer
Stops safely after a maximum number of turns

Each trace contains:

Original user message
Timestamp start & end
Every turn the model took
Exact tool name + arguments used
Full tool result
How long each tool call took (ms)
Whether the tool call succeeded
Final answer from the model
Overall status
