# script/set.ps1
$env:PYTHONPATH="$(Get-Location)\src"
uv run python src/main.py --reload