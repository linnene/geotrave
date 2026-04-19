"""
Description: GeoTrave Debug UI & Manual Simulator
Mapping: Tooling for src/agent/graph.py visualization
Priority: P2 - Developer debugging tool
Main Test Items:
1. Streamlit State Initialization (P2)
2. Graph Workflow Visualization & Interactive Loop (P2)
Note: This is not a pytest file but a functional verification tool.
"""

import streamlit as st
import uuid
import sys
import os
import asyncio

# Setup path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(root_path, "src") not in sys.path:
    sys.path.append(os.path.join(root_path, "src"))

from src.agent.graph import graph_app

# --- UI Configuration ---
st.set_page_config(page_title="GeoTrave Debug UI", layout="wide", initial_sidebar_state="expanded")
st.title("GeoTrave Agent 交互调试箱")
st.caption("基于 Streamlit 的 Agent 工作流可视化工具，用于验证状态流转与逻辑召回。")

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "travel_state" not in st.session_state:
    st.session_state.travel_state = {}

# --- Sidebar: State Inspector ---
with st.sidebar:
    st.header(" 状态检视器")
    st.info(f"Thread ID: `{st.session_state.thread_id}`")
    
    st.divider()
    
    user_profile = st.session_state.travel_state.get("user_profile") or {}
    
    # 核心指标
    st.subheader(" 核心需求")
    c1, c2 = st.columns(2)
    with c1:
        dest = user_profile.get("destination", "未确定")
        st.metric("目的地", ", ".join(dest) if isinstance(dest, list) else dest)
        st.metric("天数", user_profile.get("days") or "-")
    with c2:
        st.metric("预算", f"{user_profile.get('budget_limit')}" if user_profile.get('budget_limit') else "-")
        st.metric("人数", user_profile.get("people_count") or "-")

    # 偏好分类
    with st.expander(" 偏好与避雷", expanded=True):
        st.write("**偏好:**", user_profile.get("preferences") or "无")
        st.write("**避雷:**", user_profile.get("avoidances") or "无")
        
    # 其他细节
    with st.expander(" 细节要求", expanded=False):
        for k in ["accommodation", "dining", "transportation", "pace", "activities"]:
            v = user_profile.get(k)
            if v: st.write(f"**{k.title()}**: {v}")

    # 模型标记
    st.divider()
    st.subheader(" 决策标记")
    st.info(f"当前意图: `{st.session_state.travel_state.get('latest_intent', 'None')}`")
    st.warning(f"触发研究: `{st.session_state.travel_state.get('needs_research', False)}`")

# --- Main Interaction Area ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("说出你的旅行计划..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        # 这里集成 Graph 调用
        async def run_agent():
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            resp_text = ""
            async for event in graph_app.astream(
                {"user_input": prompt}, config, stream_mode="values"
            ):
                if "messages" in event:
                    resp_text = event["messages"][-1].content
                    response_placeholder.markdown(resp_text)
                # 更新侧边栏数据源
                st.session_state.travel_state = event
            return resp_text

        final_response = asyncio.run(run_agent())
        st.session_state.messages.append({"role": "assistant", "content": final_response})
        st.rerun()

# --- Search History (Bottom Area) ---
search_data = st.session_state.travel_state.get("search_data", {})
if search_data:
    st.divider()
    st.subheader(" 研究员工作区")
    if search_data.get("weather_info"):
        st.info(f" 目的地天气: {search_data['weather_info']}")
    
    with st.expander("查看生成的检索词与原始结果"):
        st.json(search_data)