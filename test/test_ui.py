import streamlit as st
import uuid
import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.graph import graph_app

st.set_page_config(page_title="GeoTrave Debug UI", layout="wide")

st.title("GeoTrave Agent 测试")
st.markdown("---")

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "travel_state" not in st.session_state:
    st.session_state.travel_state = {}

# 侧边栏：显示内部状态
with st.sidebar:
    st.header("TravelState")
    st.info(f"Thread ID: `{st.session_state.thread_id}`")
    
    # 辅助函数：显示字典
    def display_state_field(label, data):
        if data:
            st.subheader(label)
            st.json(data)
        else:
            st.write(f"*{label} 尚无数据*")

    display_state_field("HardConstraints", st.session_state.travel_state.get("hard_constraints"))
    display_state_field("SoftPreferences", st.session_state.travel_state.get("soft_preferences"))
    
    # 新增：展示白板中的所有其他关键信息
    st.markdown("---")
    st.subheader("Core State")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Destination", st.session_state.travel_state.get("destination") or "未确定")
        st.metric("Days", st.session_state.travel_state.get("days") or "未知")
    with col2:
        st.metric("BudgetLimit", f"¥{st.session_state.travel_state.get('budget_limit')}" if st.session_state.travel_state.get('budget_limit') else "未设置")
        # 兼容处理：people 可能是 list 也可能是 int
        people_val = st.session_state.travel_state.get("people")
        display_people = 0
        if isinstance(people_val, list):
            display_people = len(people_val)
        elif isinstance(people_val, (int, float)):
            display_people = int(people_val)
        st.metric("People", display_people)

    # 展示标签
    if st.session_state.travel_state.get("tags"):
        st.write("**TAG:**")
        st.write(", ".join([f"`{tag}`" for tag in st.session_state.travel_state.get("tags")]))# type:ignore

    # 新增：展示研究员检索内容
    st.markdown("---")
    st.subheader("Researcher result")
    if st.session_state.travel_state.get("retrieval_context"):
        with st.expander("查看完整检索内容", expanded=False):
            st.write(st.session_state.travel_state.get("retrieval_context"))
    else:
        st.write("*暂无检索内容*")

    if st.button("RESET"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.travel_state = {}
        st.rerun()

# 聊天界面
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("输入你的旅行需求 (例如: 我想去大理，预算5000)"):
    # 用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 Agent 逻辑
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    
    with st.chat_message("assistant"):
        with st.spinner("Agent 正在思考并执行任务..."):
            try:
                # 获取当前最新的状态，或者基于历史执行
                # 注意：这里只发送最新的一条消息，MemorySaver 会自动根据 thread_id 补偿历史
                inputs = {"messages": [("user", prompt)]}
                
                # 显式传递 config 确保 thread_id 被 MemorySaver 识别
                result = asyncio.run(graph_app.ainvoke(inputs, config=config))# type:ignore
                
                # 更新状态显示
                st.session_state.travel_state = result
                
                # 获取最后一条 AI 消息作为回复
                if result.get("messages"):
                    last_msg = result["messages"][-1]
                    # 兼容 BaseMessage 或 dict
                    if hasattr(last_msg, 'content'):
                        content = last_msg.content
                    elif isinstance(last_msg, dict):
                        content = last_msg.get("content", str(last_msg))
                    else:
                        content = str(last_msg)
                    
                    st.markdown(content)
                    st.session_state.messages.append({"role": "assistant", "content": content})
                else:
                    st.error("Agent 返回了空消息。")
            except Exception as e:
                st.error(f"执行出错: {str(e)}")
                import traceback
                
    # 强制刷新侧边栏状态，并保持页面位置
    st.rerun()
