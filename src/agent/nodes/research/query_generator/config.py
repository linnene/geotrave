# QueryGenerator Node Configuration
TEMPERATURE = 0.6
"""
QueryGenerator 需要足够的发散性来生成多样化的搜索维度和关键词。
0.6 的温度让 LLM 在生成搜索策略时具有明显的联想多样性，避免每次输出高度一致。
"""
HISTORY_LIMIT = 3
"""
QueryGenerator 需要一定的历史对话上下文来准确理解用户的需求和偏好，但我们仍然希望限制它，以避免过多无关信息干扰模型，并确保它专注于最相关的信息。
"""
MAX_TOKENS = 1500
"""
QueryGenerator 需要生成相对简洁的输出，主要是针对用户需求的核心诉求和关键信息的提取，因此我们将最大 token 数限制在 1500，以确保输出的精炼和高效。
"""