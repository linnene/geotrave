import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# LLM 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY environment variable is not set. Please configure it in your environment or .env file."
    )

# LLM 模型配置
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
MODEL_ID = os.getenv("MODEL_ID", "deepseek-chat")

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
