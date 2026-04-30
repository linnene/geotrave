"""BM25 文档检索配置参数。"""

# BM25 调参
BM25_K1 = 1.5
BM25_B = 0.75

# 相关度阈值 — BM25 得分低于此值的文档被丢弃
BM25_SCORE_THRESHOLD = 0.5

# 单次查询最大返回数（安全阀）
MAX_DOC_RESULTS = 5

# 文档摘要展示长度（字符）
SNIPPET_LENGTH = 300
