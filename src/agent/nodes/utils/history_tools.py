"""
Module: src.agent.nodes.utils.history_tools
Responsibility: Node-level utilities for formatting and slicing conversation history.
"""

from typing import List
from langchain_core.messages import BaseMessage

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
        
    relevant_messages = messages[-(history_limit + 1):-1]
    
    chat_history = []
    for m in relevant_messages:
        role = "user" if m.type == "human" else "assistant"
        content = m.content if isinstance(m.content, str) else str(m.content)
        chat_history.append(f"{role}: {content}")
        
    return "\n".join(chat_history) if chat_history else "无对话历史"
