import os
import json
import streamlit as st
from collections import deque
from langchain_groq import ChatGroq
from langchain.tools import tool

# --- INITIAL CONFIG ---
st.set_page_config(page_title="Mahotsav AI Guide", page_icon="🎓", layout="wide")
os.environ["GROQ_API_KEY"] = ""

# --- DATA LOADER ---
@st.cache_data
def load_data():
    with open("campus_data.json") as f:
        return json.load(f)["locations"]

campus_data = load_data()

# --- INTERNAL TOOLS (Hidden from LLM direct call, used inside ask_ai) ---

def normalize_place(query):
    if not query: return None
    q = query.lower().strip()
    for key, info in campus_data.items():
        if key in q.replace(" ", "_") or info["name"].lower() in q:
            return key
        if any(word in q for word in info.get("search_keywords", [])):
            return key
    return None

def find_path(start, end):
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == end: return path
        for neighbor in campus_data[node].get("connected_to", []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None

# --- LLM ENGINE ---

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)

def ask_ai(user_input):
    """
    Every query passes through here. 
    The LLM is provided with the campus context to answer naturally.
    """
    
    # 1. Prepare Context from JSON
    # We provide a condensed version of the campus data to the LLM's prompt
    context_str = ""
    for k, v in campus_data.items():
        context_str += f"- {v['name']} (Key: {k}): {v['description']}. Navigation: {v['navigation']}\n"

    system_prompt = f"""
    You are the official Vignan Mahotsav 2026 AI Guide. 
    Your goal is to be helpful, witty, and accurate.
    
    CAMPUS CONTEXT:
    {context_str}
    
    INSTRUCTIONS:
    1. If the user asks for directions (how to go, reach, way to), identify the START and END locations.
    2. If the user just asks about a place, describe its events, floors, and facilities using the context.
    3. If you provide directions, format them clearly using Step 1, Step 2, etc. 
    - Format steps as:
    Step 1:
    Step 2:
    Step 3:
    4. If a location isn't in the context, politely say it's not part of the Mahotsav 2026 map.
    5. Always maintain a friendly student-peer persona.
    """

    # 2. Logic Injection: Handle Pathfinding within the response
    # We check if the user is asking for a route to provide the exact path to the LLM
    route_context = ""
    start_key = normalize_place(user_input.split("from")[-1]) if "from" in user_input else "main_gate"
    end_key = normalize_place(user_input)
    
    if end_key:
        path = find_path(start_key or "main_gate", end_key)
        if path:
            route_context = f"\nTECHNICAL ROUTE DATA: The path is {' -> '.join([campus_data[p]['name'] for p in path])}."

    # 3. Final LLM Call
    response = llm.invoke([
        {"role": "system", "content": system_prompt + route_context},
        {"role": "user", "content": user_input}
    ])
    
    return response.content

# --- STREAMLIT UI ---
st.title("🎓 Vignan Mahotsav 2026 AI Guide")
st.caption("Now powered entirely by Llama 3.1 for more natural conversations.")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! 👋 I'm your Mahotsav Guide. How can I help you today?"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            ans = ask_ai(prompt)
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})