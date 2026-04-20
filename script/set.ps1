# script/set.ps1
$env:PYTHONPATH="."
uv run python src/main.py --debug --reload