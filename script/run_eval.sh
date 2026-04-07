#!/bin/bash
# GeoTrave Agent Evaluation Runner (Linux/macOS)

echo "--------------------------------------------------"
echo "GeoTrave Agent 评估启动中 (Linux/macOS)..."
echo "--------------------------------------------------"

# 使用项目默认的 python 解释器运行 pytest
python -m pytest test/eval/test_agent_workflow.py -v -s --asyncio-mode=strict

# 返回测试结果状态码
exit $?
