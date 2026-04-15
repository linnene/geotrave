import streamlit as st
import uuid
import sys
import os
import asyncio


from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from threading import current_thread

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

    user_profile = st.session_state.travel_state.get("user_profile") or {}

    display_state_field("Preferences (偏好)", user_profile.get("preferences"))
    display_state_field("Avoidances (避雷)", user_profile.get("avoidances"))
    
    # 新增：展示次要需求偏好分类
    st.markdown("---")
    st.subheader("Secondary Details")
    for k in ["accommodation", "dining", "transportation", "pace", "activities"]:
        v = user_profile.get(k)
        if v:
            st.write(f"**{k.capitalize()}**: {v}")

    # 新增：展示白板中的所有其他关键信息
    st.markdown("---")
    st.subheader("Core State")
    st.info(f"Latest Intent: `{st.session_state.travel_state.get('latest_intent', 'None')}`")
    st.info(f"Needs Research: `{st.session_state.travel_state.get('needs_research', False)}`")
    col1, col2 = st.columns(2)
    with col1:
        dest_val = user_profile.get("destination")
        dest_display = ", ".join(dest_val) if isinstance(dest_val, list) else (dest_val or "未确定")
        st.metric("Destination", dest_display)
        st.metric("Days", user_profile.get("days") or "未知")
    with col2:
        st.metric("BudgetLimit", f"¥{user_profile.get('budget_limit')}" if user_profile.get('budget_limit') else "未设置")
        # 兼容处理：people 可能是 list 也可能是 int
        people_val = user_profile.get("people_count")
        st.metric("People", people_val if people_val else 0)

    # 新增：展示研究员检索内容
    st.markdown("---")
    st.subheader("Researcher Result")
    
    # 获取新的结构化数据
    search_data = st.session_state.travel_state.get("search_data", {})
    queries = search_data.get("query_history", [])
    if queries:
        st.write("**本次由大模型生成的检索词 (Queries):**")
        for q in queries:
            st.caption(f"- `{q}`")
            
    retrieval_results = search_data.get("retrieval_results") or []
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
            
            # 使用两个容器：上面放回复（立刻显示），下面放轨迹
            reply_container = st.empty()
            status_container = st.status("Agent 处理轨迹...", expanded=True)
            trace_logs = []
            
            # 抓取当前的上下文
            ctx = get_script_run_ctx()
            
            async def run_graph():
                # 内部显式重新挂载
                add_script_run_ctx(ctx=ctx)
                
                async for event in graph_app.astream(inputs, config=config, stream_mode="updates"): # type: ignore
                    
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
                        
                        if node_name == "analyzer":
                            # 分析师有结果了，立刻把回复上屏，不被 Researcher 的网络耗时阻塞
                            if "messages" in node_state and node_state["messages"]:
                                last_msg = node_state["messages"][-1]
                                content = last_msg.content if hasattr(last_msg, 'content') else (last_msg.get("content") if isinstance(last_msg, dict) else str(last_msg))
                                reply_container.markdown(content)
                                
                            if "needs_research" in node_state:
                                needs_research = node_state["needs_research"]
                                sub_msg = f"    ↳ 需要联网检索: `{needs_research}`\n"
                        if node_name == "researcher" and "search_data" in node_state:
                            search_data = node_state["search_data"]
                            stats = search_data.get("retrieval_stats")
                            if stats:
                                total = stats.get("total_fetched", 0)
                                filtered = stats.get("total_filtered", 0)
                                valid = stats.get("valid_count", 0)
                                sub_msg = f"    ↳ 检索统计: 累计获取 {total} 条数据，质检过滤掉 {filtered} 条无关内容，保留 {valid} 条。\n"
                                status_container.write(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ 检索统计: 共获取 `{total}` 条数据，命中过滤 `{filtered}` 条，剩 `{valid}` 条有效内容。")
                                log_msg += sub_msg

                        trace_logs.append(log_msg)

            asyncio.run(run_graph())
            status_container.update(label="处理完成!", state="complete", expanded=False)
            
            # 记录轨迹到历史
            if trace_logs:
                st.session_state.messages.append({"role": "assistant", "is_trace": True, "label": "Agent 处理轨迹", "content": "\n".join(trace_logs)})
            
            # 获取最终的完整状态
            result_state = graph_app.get_state(config) # type: ignore
            result = result_state.values
            st.session_state.travel_state = result
            
            # 以从状态图中提取的最终回复落盘到历史中
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                content = last_msg.content if hasattr(last_msg, 'content') else (last_msg.get("content") if isinstance(last_msg, dict) else str(last_msg))
                # 因为刚刚通过 reply_container 实时渲染过了，所以这里不仅更新历史，同时为了保险起见重新填充一下
                reply_container.markdown(content)
                st.session_state.messages.append({"role": "assistant", "content": content})
            else:
                st.error("Agent 返回了空消息。")
        except Exception as e:
            st.error(f"执行出错: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            
    # 强制刷新侧边栏状态，并保持页面位置
    st.rerun()
