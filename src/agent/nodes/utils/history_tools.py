"""
Module: src.agent.nodes.utils.history_tools
Responsibility: Node-level utilities for formatting conversation history and building audit traces.
"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage

from typing import Any, Dict, Optional

from src.agent.state import TraceLog

def format_recent_history(messages: List[BaseMessage], history_limit: int = 5) -> str:
    """
    提取最近 N 条对话记录并格式化为字符串。
    
    Args:
        messages: 全量消息列表。
        history_limit: 提取的历史记录条数限制。
        
    Returns:
        格式化后的对话历史字符串，如:
        user: ...
        assistant: ...
    """
    if not messages:
        return "无对话历史"
        
    relevant_messages = messages[-history_limit:]
    
    chat_history = []
    for m in relevant_messages:
        role = "user" if m.type == "human" else "assistant"
        content = m.content if isinstance(m.content, str) else str(m.content)
        chat_history.append(f"{role}: {content}")
        
    return "\n".join(chat_history) if chat_history else "无对话历史"

def build_trace(node: str, status: str, latency_ms: int, detail: Dict[str, Any], token_usage: Optional[Dict[str, int]] = None) -> TraceLog:
    kwargs: Dict[str, Any] = {"node": node, "status": status, "latency_ms": latency_ms, "detail": detail}
    if token_usage:
        kwargs["token_usage"] = token_usage
    return TraceLog(**kwargs)
