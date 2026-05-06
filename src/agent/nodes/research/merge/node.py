import time
from typing import Any, Dict

from src.agent.state import TravelState
from src.utils.logger import get_logger
from src.agent.nodes.utils import build_trace

logger = get_logger("ResearchMergeNode")


async def research_merge_node(state: TravelState) -> Dict[str, Any]:
    """ResearchMerge Node — 并行 research_loop 结果汇聚点。

    research_data 已由 _merge_research_manifest reducer 自动合并，
    本节点只需清理维度控制字段并记录汇聚统计。
    """
    start_time = time.time()

    research_data = state.get("research_data")
    hashes_count = sum(len(v) for v in research_data.research_hashes) if research_data else 0

    dims = state.get("planned_dimensions", [])
    logger.info(
        "ResearchMerge — aggregating %d dimensions, total hashes=%d",
        len(dims), hashes_count
    )

    trace = build_trace(
        "research_merge",
        "SUCCESS",
        latency_ms=int((time.time() - start_time) * 1000),
        detail={
            "dimensions_merged": dims,
            "total_hashes": hashes_count,
        }
    )

    return {
        "planned_dimensions": [],
        "focus_dimension": None,
        "trace_history": [trace],
    }
