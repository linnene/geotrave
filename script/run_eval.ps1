# GeoTrave Agent Evaluation Runner (Windows PowerShell)

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "GeoTrave Agent test(Windows)..." -ForegroundColor Cyan
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

# 执行 pytest 并传递参数
python -m pytest test/eval/test_agent_workflow.py -v -s --asyncio-mode=strict

# 将 Pytest 的退出代码传递给 shell
exit $LASTEXITCODE
