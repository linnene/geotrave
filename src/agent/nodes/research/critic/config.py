"""
Module: src.agent.nodes.research.config
Responsibility: Critic node constants — quality thresholds and loop control parameters.
"""

# 混合退出阈值: 单轮至少通过 N 条结果才允许 LLM 决定退出
PASS_COUNT_MIN = 3

# 硬上限: 无论 LLM 如何决策，最多迭代 N 轮后强制退出
MAX_LOOPS = 2

# 评分任务需低温度以保证一致性
CRITIC_TEMPERATURE = 0.3

# 每批送入 Critic LLM 的结果条数（控制 token 消耗）
CRITIC_BATCH_SIZE = 5

# Layer 3 最低通过阈值: relevance 和 utility 均需 >= 此值
MIN_SCORE_THRESHOLD = 40

# LLM 最大输出 token
MAX_TOKENS = 3000
