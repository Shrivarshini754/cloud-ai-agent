import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://load_balancer:80")

st.set_page_config(page_title="Cloud-Native Spanish AI Tutor", layout="wide")

# Custom UI Styling
st.markdown("""
<style>
    /* Main background gradient and font */
    .stApp {
        background: radial-gradient(circle at 50% -20%, #4c2889, #0f0c29 50%, #151136 100%);
        color: #e2d9f3;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar glassmorphism styling */
    [data-testid="stSidebar"] {
        background-color: rgba(20, 16, 45, 0.6) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    [data-testid="stSidebar"] * {
        color: #e2d9f3 !important;
    }
    
    /* Chat message glowing cards */
    .stChatMessage {
        background: rgba(30, 24, 70, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
    }
    
    /* Chat input box styling & text visibility */
    [data-testid="stChatInput"] {
        background-color: rgba(30, 24, 70, 0.9) !important;
        border: 1px solid rgba(138, 92, 246, 0.6) !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #ffffff !important;
    }
    
    /* Header and metric adjustments */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    hr {
        border-color: rgba(255,255,255,0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar: Architecture Diagnostics
with st.sidebar:
    st.markdown("### ☁️ Cloud Architecture")
    st.divider()
    st.markdown("#### 🚀 CI/CD Pipeline")
    st.markdown("[![Build Status](https://github.com/alex-dev123/cloud-native-ai-tutor/actions/workflows/deploy.yml/badge.svg)](https://github.com/alex-dev123/cloud-native-ai-tutor)")
    st.divider()
    st.markdown("#### ⚖️ Load Balancer & Replicas")
    try:
        health_data = requests.get(f"{BACKEND_URL}/health", timeout=3).json()
        st.metric(label="Cluster Health", value=health_data["status"])
        st.caption(f"**Active Replica ID:** `{health_data['compute_node_id']}`")
    except Exception:
        st.error("Compute Nodes Unreachable")
    st.divider()
    st.markdown("#### ⚡ In-Memory Cache")
    st.caption("**Technology:** Redis Container (Active)")

# Main Header
st.title("🇪🇸 Spanish AI Tutor")
st.caption("Cloud-Native Distributed System: Streamlit Frontend ➔ Nginx Load Balancer ➔ FastAPI Replicas ➔ Redis Cache")

# 1. Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Render all past messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 3. Handle new user input
prompt = st.chat_input("Ask tu tutor de español una pregunta...")

if prompt:
    # Append and render user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
        
    # Query backend and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                system_prompt = "You are a helpful A1-level Spanish language tutor. Always incorporate Spanish phrases, grammar tips, or cultural context into your responses while explaining clearly."
                full_prompt = f"{system_prompt}\n\nStudent: {prompt}"

                response = requests.post(
                    f"{BACKEND_URL}/chat", 
                    json={"prompt": full_prompt, "model": "gemini-3.8-flash"},
                    timeout=60
                )
                
                if response.status_code == 200:
                    res = response.json()
                    bot_reply = res["response"]
                    st.write(bot_reply)
                    
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    
                    cols = st.columns(2)
                    with cols[0]:
                        if res.get("cache_status") == "hit":
                            st.success(f"⚡ Cache Hit ({res.get('latency', 0):.4f}s)")
                        else:
                            st.info(f"🔄 Cache Miss ({res.get('latency', 0):.4f}s)")
                    with cols[1]:
                        st.caption("Served by Cluster")
                else:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except Exception:
                        error_detail = response.text
                    st.error(f"Backend Error: {error_detail}")
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")