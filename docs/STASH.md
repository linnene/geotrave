# 临时代码放置或备忘 (STASH)

## 旧版 Prompt 留存区

### 1. 严格过滤策略 (已弃用)
`python
_RESEARCH_FILTER_TEMPLATE = """You are a Quality Control Assistant analyzing a search engine result snippet.
Your job is to determine if the retrieved snippet is directly relevant to the user's explicit query context.
...
# Note: Abandoned because it was too strict and often discarded short but useful search engine results. 
# Replaced with a more lenient approach that assumes relevance unless explicitly contradictory.

## 技术栈与设计备忘

- **测试设计**：
  - 测试用例目前依赖 pytest + unittest.mock.MagicMock。
  - 测试通过拦截 _RESEARCH_FILTER_TEMPLATE 的输出来模拟 LLM 判断（例如返回 "YES" 或 "NO \n Reason: Too short"）。
  
- **代码规范 (Karpathy Guidelines)**:
  - 已挂载于 .github/copilot-instructions.md。
  - 规定：修改任何代码时遵循不假设、最简原则、外科手术式修改、目标驱动的方针。
