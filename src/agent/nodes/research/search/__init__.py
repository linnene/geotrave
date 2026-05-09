from .node import search_node

# 抑制 search 层工具节点的 INFO 日志（参数/结果过于冗长）
import logging
for _name in ("SearchNode", "SearchTools", "WebSearch", "WeatherSearch", "DocumentManager"):
    logging.getLogger(_name).setLevel(logging.WARNING)
