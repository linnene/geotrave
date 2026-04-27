import streamlit as st
import uuid
import json
import asyncio
import sys
import os
from typing import cast

# 将项目根目录添加到 pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage, AIMessage
from src.agent.graph import get_travel_app
from src.agent.state.state import TravelState

# 配置页面
st.set_page_config(page_title="GeoTrave Agent 实验室", layout="wide")

st.title("🧪 GeoTrave Agent 2.0 实验室 (Direct Mode)")
st.markdown("---")

# 初始化 Session ID 和 状态
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "latest_state" not in st.session_state:
    st.session_state.latest_state = {}

# 侧边栏：实时状态监控
with st.sidebar:
    st.header("🔍 实时状态监控")
    st.info(f"Thread ID: `{st.session_state.session_id}`")
    
    if st.button("🔄 重置会话"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.session_state.latest_state = {}
        st.rerun()

    if st.session_state.latest_state:
        st.divider()
        st.subheader("📍 节点流转 (Route)")
        route = st.session_state.latest_state.get("route_metadata")
        if route:
            # 兼容 Pydantic 和 Dict
            next_node = getattr(route, "next_node", route.get("next_node") if isinstance(route, dict) else "unknown")
            reason = getattr(route, "reason", route.get("reason") if isinstance(route, dict) else "")
            st.success(f"**Next Node**: `{next_node}`")
            st.caption(f"Reason: {reason}")
        
        with st.expander("👤 User Profile", expanded=True):
            profile = st.session_state.latest_state.get("user_profile")
            if profile:
                st.json(profile.model_dump() if hasattr(profile, "model_dump") else profile)

        with st.expander("📊 Research Data (Verified)"):
            research = st.session_state.latest_state.get("research_data")
            if research:
                verified = getattr(research, "verified_results", {})
                st.write(f"Total Verified Hashes: `{len(verified)}`")
                if verified:
                    st.json(verified)
            else:
                st.caption("No research data yet.")
        
        with st.expander("📜 Trace History"):
            traces = st.session_state.latest_state.get("trace_history", [])
            for t in reversed(traces):
                status_val = getattr(t, "status", t.get("status") if isinstance(t, dict) else "unknown")
                node_val = getattr(t, "node", t.get("node") if isinstance(t, dict) else "unknown")
                latency_val = getattr(t, "latency_ms", t.get("latency_ms") if isinstance(t, dict) else 0)
                status_color = "🟢" if status_val == "SUCCESS" else "🔴"
                st.markdown(f"{status_color} **{node_val}** ({latency_val}ms)")
        
        with st.expander("🛡️ 全局 State 详情"):
            # 过滤掉庞大的 messages 以便查看
            debug_state = {k: v for k, v in st.session_state.latest_state.items() if k != "messages"}
            def serialize(obj):
                if hasattr(obj, "model_dump"): return obj.model_dump()
                return str(obj)
            st.json(json.loads(json.dumps(debug_state, default=serialize)))

# 聊天主界面
for msg_type, content in st.session_state.chat_history:
    with st.chat_message("user" if msg_type == "human" else "assistant"):
        st.markdown(content)

# 处理输入
if prompt := st.chat_input("输入指令..."):
    st.session_state.chat_history.append(("human", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Graph 运行中..."):
            # 构造输入并进行类型转换满足 Pylance
            input_state = cast(TravelState, {"messages": [HumanMessage(content=prompt)]})
            config = {"configurable": {"thread_id": st.session_state.session_id}}
            
            # 手动运行异步 Graph
            async def run_agent():
                app = await get_travel_app()
                return await app.ainvoke(input_state, config=config)
            
            try:
                final_state = asyncio.run(run_agent())
                st.session_state.latest_state = final_state
                
                # 获取最后一条 AI 消息
                msgs = final_state.get("messages", [])
                ai_reply = "未触发回复节点"
                # 直接获取 AIMessage 实例，langgraph 会自动反序列化
                for m in reversed(msgs):
                    # 检查类型或者类名（防止反序列化后的奇怪类型判断失败）
                    if hasattr(m, 'type') and m.type == 'ai':
                        ai_reply = m.content
                        break
                    elif isinstance(m, AIMessage):
                        ai_reply = m.content
                        break
                
                st.markdown(ai_reply)
                st.session_state.chat_history.append(("ai", ai_reply))
                st.rerun() # 强制刷新以更新侧边栏
                
            except Exception as e:
                st.error(f"Graph 执行失败: {str(e)}")
                st.exception(e)
