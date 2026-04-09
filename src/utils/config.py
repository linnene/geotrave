import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# --- 核心/分析师 (Analyzer) 模型配置 ---
ANALYZER_MODEL_API_KEY = os.getenv("ANALYZER_MODEL_API_KEY", "")
ANALYZER_MODEL_BASE_URL = os.getenv("ANALYZER_MODEL_BASE_URL", "https://api.deepseek.com")
ANALYZER_MODEL_ID = os.getenv("ANALYZER_MODEL_ID", "deepseek-chat")

# --- 研究员 (Researcher) 专属模型配置 ---
RESEARCHER_MODEL_API_KEY = os.getenv("RESEARCHER_MODEL_API_KEY", "")
RESEARCHER_MODEL_BASE_URL = os.getenv("RESEARCHER_MODEL_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
RESEARCHER_MODEL_ID = os.getenv("RESEARCHER_MODEL_ID", "gemini-1.5-flash")

# --- 规划师 (Planner) 专属模型配置 (预留) ---
PLANNER_MODEL_API_KEY = os.getenv("PLANNER_MODEL_API_KEY", "")
PLANNER_MODEL_BASE_URL = os.getenv("PLANNER_MODEL_BASE_URL", "https://api.openai.com/v1")
PLANNER_MODEL_ID = os.getenv("PLANNER_MODEL_ID", "gpt-4o")

# --- 通用 API KEY 校验 ---
if not (ANALYZER_MODEL_API_KEY or RESEARCHER_MODEL_API_KEY):
    # 如果核心 API Key 全都缺失，则报错
    pass # 暂时不强制中断，允许用户在 .env 中分别配置

# Embedding 模型配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
EMBEDDING_MODEL_API_KEY = os.getenv("EMBEDDING_MODEL_API_KEY", "")
EMBEDDING_MODEL_BASE_URL = os.getenv("EMBEDDING_MODEL_BASE_URL", "")

# LLM 建议配置
PLANNING_TEMPERATURE = 0.7
MAX_TOKENS = 4096
LLM_TIMEOUT = 60

# ChromaDB 向量数据库配置
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./data/chroma")
DB_TIMEOUT = 60

# 日志配置
LOG_LEVEL = "DEBUG"
