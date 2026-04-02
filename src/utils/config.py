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
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 旅游规划建议配置
PLANNING_TEMPERATURE = 0.7
MAX_TOKENS = 4096
TIMEOUT = 60
