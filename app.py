import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from procurement.graph import builder
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# 1. Page Setup
st.set_page_config(page_title="SME Procurement Agent", page_icon="🏢")
st.title("🏢 SME Procurement Assistant")
st.write("Ask me to check inventory and create requisitions.")

# 2. Initialize Session State & Graph
if "messages" not in st.session_state:
    st.session_state.messages = []

# Compile the graph once and store it in the session
if "graph" not in st.session_state:
    st.session_state.graph = builder.compile(checkpointer=MemorySaver())

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit-session-1"

config = {"configurable": {"thread_id": st.session_state.thread_id}}
graph = st.session_state.graph

# 3. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tool_calls" in msg and msg["tool_calls"]:
            st.info(f"🛠️ Tool called: {msg['tool_calls'][0]['name']}")

# 4. Check if the graph is currently paused for approval
state = graph.get_state(config)
is_paused = bool(state.next and "approval_gate" in state.next)

# 5. Handle Approval Buttons
if is_paused:
    st.warning("⚠️ **Human Approval Required:** The agent wants to create a draft requisition.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve", use_container_width=True):
            with st.spinner("Executing approved action..."):
                for event in graph.stream(Command(resume="approve"), config, stream_mode="values"):
                    pass
                st.session_state.messages.append({"role": "assistant", "content": "✅ Requisition approved and created successfully!"})
                st.rerun()
    with col2:
        if st.button("❌ Reject", use_container_width=True):
            with st.spinner("Canceling action..."):
                for event in graph.stream(Command(resume="reject"), config, stream_mode="values"):
                    pass
                st.session_state.messages.append({"role": "assistant", "content": "❌ Requisition rejected by human."})
                st.rerun()

# 6. Chat Input (Disabled if waiting for approval)
if prompt := st.chat_input("E.g., Check ITM-001. If below reorder point, draft a requisition...", disabled=is_paused):
    
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run the graph
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            input_state = {"messages": [("user", prompt)]}
            
            # Stream the graph execution
            for event in graph.stream(input_state, config, stream_mode="values"):
                pass # We just let it run to completion or pause
                
            # Get the latest AI message
            new_state = graph.get_state(config)
            last_message = new_state.values["messages"][-1]
            
            # If it paused, trigger a rerun to show the approval buttons
            if new_state.next and "approval_gate" in new_state.next:
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "I have prepared the draft requisition. **Please approve or reject it below.**"
                })
                st.rerun()
            
            # If it finished normally, display the final text
            elif last_message.content:
                st.markdown(last_message.content)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": last_message.content,
                    "tool_calls": last_message.tool_calls if hasattr(last_message, 'tool_calls') else None
                })