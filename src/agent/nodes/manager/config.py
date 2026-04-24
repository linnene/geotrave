"""
Module: src.agent.nodes.manager.config
Responsibility: Local configuration for the Manager node.
"""

TEMPERATURE = 0.0 # Manager 需要极高的确定性

HISTORY_LIMIT = 4  # Manager 需要一定的历史上下文来做出决策，但不需要过多

MAX_TOKENS = 500

NODE_HISTORY_LIMIT = 5