import streamlit as st
import uuid
import sys
import os
import asyncio


root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(root_path, "src"))
sys.path.append(root_path)

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

    core_req = st.session_state.travel_state.get("core_requirements") or {}
    conv_summary = st.session_state.travel_state.get("conversation_summary") or {}

    display_state_field("Core Constraints", conv_summary.get("core_constraints"))
    display_state_field("Temp Preferences", conv_summary.get("temp_preferences"))
    display_state_field("Rejected Items", conv_summary.get("rejected_items"))
    
    # 新增：展示白板中的所有其他关键信息
    st.markdown("---")
    st.subheader("Core State")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Destination", core_req.get("destination") or "未确定")
        st.metric("Days", core_req.get("days") or "未知")
    with col2:
        st.metric("BudgetLimit", f"¥{core_req.get('budget_limit')}" if core_req.get('budget_limit') else "未设置")
        # 兼容处理：people 可能是 list 也可能是 int
        people_val = core_req.get("people")
        display_people = 0
        if isinstance(people_val, list):
            display_people = len(people_val)
        elif isinstance(people_val, (int, float)):
            display_people = int(people_val)
        st.metric("People", display_people)

    # 展示标签
    if core_req.get("tags"):
        st.write("**TAG:**")
        st.write(", ".join([f"`{tag}`" for tag in core_req.get("tags")]))# type:ignore

    # 新增：展示研究员检索内容
    st.markdown("---")
    st.subheader("Researcher Result")
    
    # 获取新的结构化数据
    search_data = st.session_state.travel_state.get("search_data", {})
    retrieval_results = search_data.get("retrieval_results")
    if retrieval_results:
        with st.expander(f"查看结构化检索结果 ({len(retrieval_results)}条)", expanded=False):
            for i, item in enumerate(retrieval_results):
                # 如果是 Pydantic 对象或 Dict，尝试友好展示
                source_tag = f"[{item.get('source', 'unknown').upper()}]" if isinstance(item, dict) else f"[{item.source.upper()}]"
                title = item.get('title') if isinstance(item, dict) else item.title
                content = item.get('content') if isinstance(item, dict) else item.content
                
                st.markdown(f"**{i+1}. {source_tag} {title}**")
                st.text(content[:200] + "..." if len(content) > 200 else content)
                st.markdown("---")
    
    # 保留旧的文本显示用于对比
    retrieval_context = search_data.get("retrieval_context")
    if retrieval_context:
        with st.expander("查看原始检索文本", expanded=False):
            st.write(retrieval_context)
    elif not retrieval_results:
        st.write("*暂无检索内容*")

    if st.button("RESET"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.travel_state = {}
        st.rerun()

# 聊天界面
for message in st.session_state.messages:
    if message.get("is_trace"):
        with st.status(message.get("label", "Agent 处理轨迹"), state="complete", expanded=False):
            st.markdown(message["content"])
    else:
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
        try:
            inputs = {"messages": [("user", prompt)]}
            
            status_container = st.status("Agent 处理轨迹...", expanded=True)
            trace_logs = []
            
            async def run_graph():
                async for event in graph_app.astream(inputs, config=config, stream_mode="updates"):
                    for node_name, node_state in event.items():
                        log_msg = f"✅ 执行节点: **{node_name}**\n"
                        status_container.write(f"✅ 执行节点: **{node_name}**")
                        
                        # 提取节点中的关键信息进行展示
                        if node_name == "router" and "latest_intent" in node_state:
                            intent = node_state["latest_intent"]
                            if hasattr(intent, "intent"):
                                sub_msg = f"    ↳ 识别意图: `{intent.intent}`  *(置信度: {intent.confidence})*\n"
                                status_container.write(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ 识别意图: `{intent.intent}`  *(置信度: {intent.confidence})*")
                                log_msg += sub_msg
                        
                        if node_name == "analyzer" and "needs_research" in node_state:
                            needs_research = node_state["needs_research"]
                            sub_msg = f"    ↳ 需要联网检索: `{needs_research}`\n"
                            status_container.write(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ 需要联网检索: `{needs_research}`")
                            log_msg += sub_msg
                        
                        trace_logs.append(log_msg)

            asyncio.run(run_graph())
            status_container.update(label="处理完成!", state="complete", expanded=False)
            
            # 记录轨迹到历史
            if trace_logs:
                st.session_state.messages.append({"role": "assistant", "is_trace": True, "label": "Agent 处理轨迹", "content": "\n".join(trace_logs)})
            
            # 获取最终的完整状态
            result_state = graph_app.get_state(config)
            result = result_state.values
            
            # 更新状态显示
            st.session_state.travel_state = result
            
            # 获取最后一条消息作为回复
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
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
            st.code(traceback.format_exc())
            
    # 强制刷新侧边栏状态，并保持页面位置
    st.rerun()
