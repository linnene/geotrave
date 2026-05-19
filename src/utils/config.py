"""
Module: src.utils.config
Responsibility: Centralized configuration management handling environment variables, LLM parameters, and system-wide settings.
Parent Module: src.utils
Dependencies: os, python-dotenv

This module loads the `.env` file and exposes immutable global configurations 
for database connections, LLM APIs, and agent hyperparameters.
"""

import os
from dotenv import load_dotenv

# ==============================================================================
# GeoTrave Configuration 
# Loaded via .env file or Environment Variables
# ==============================================================================
load_dotenv()

# --- 1. Global LLM Configuration ---
GLOBAL_MODEL_API_KEY = os.getenv("GLOBAL_MODEL_API_KEY", "")
GLOBAL_MODEL_BASE_URL = os.getenv("GLOBAL_MODEL_BASE_URL", "")
GLOBAL_MODEL_ID = os.getenv("GLOBAL_MODEL_ID", "")

# --- 2. Node-Specific LLM Configuration ---
ANALYST_MODEL_API_KEY = os.getenv("ANALYST_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
ANALYST_MODEL_BASE_URL = os.getenv("ANALYST_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
ANALYST_MODEL_ID = os.getenv("ANALYST_MODEL_ID", GLOBAL_MODEL_ID)

RESEARCHER_MODEL_API_KEY = os.getenv("RESEARCHER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
RESEARCHER_MODEL_BASE_URL = os.getenv("RESEARCHER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
RESEARCHER_MODEL_ID = os.getenv("RESEARCHER_MODEL_ID", GLOBAL_MODEL_ID)

GATEWAY_MODEL_API_KEY = os.getenv("ROUTER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
GATEWAY_MODEL_BASE_URL = os.getenv("ROUTER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
GATEWAY_MODEL_ID = os.getenv("ROUTER_MODEL_ID", GLOBAL_MODEL_ID)

PLANNER_MODEL_API_KEY = os.getenv("PLANNER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
PLANNER_MODEL_BASE_URL = os.getenv("PLANNER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
PLANNER_MODEL_ID = os.getenv("PLANNER_MODEL_ID", GLOBAL_MODEL_ID)

# --- 4. System Base Configuration ---
# Checkpoint 数据库配置 (Sqlite)
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "database/checkpointer/checkpoints.sqlite")

# Session 元数据存储配置 (Sqlite, 可替换为 PostgreSQL)
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "database/session_store/sessions.sqlite")

RECOMMENDER_MODEL_API_KEY = os.getenv("RECOMMENDER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
RECOMMENDER_MODEL_BASE_URL = os.getenv("RECOMMENDER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
RECOMMENDER_MODEL_ID = os.getenv("RECOMMENDER_MODEL_ID", GLOBAL_MODEL_ID)

CRITIC_MODEL_API_KEY = os.getenv("CRITIC_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
CRITIC_MODEL_BASE_URL = os.getenv("CRITIC_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
CRITIC_MODEL_ID = os.getenv("CRITIC_MODEL_ID", GLOBAL_MODEL_ID)

MANAGER_MODEL_API_KEY = os.getenv("MANAGER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
MANAGER_MODEL_BASE_URL = os.getenv("MANAGER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
MANAGER_MODEL_ID = os.getenv("MANAGER_MODEL_ID", GLOBAL_MODEL_ID)

DIMENSION_PLANNER_MODEL_API_KEY = os.getenv("DIMENSION_PLANNER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
DIMENSION_PLANNER_MODEL_BASE_URL = os.getenv("DIMENSION_PLANNER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
DIMENSION_PLANNER_MODEL_ID = os.getenv("DIMENSION_PLANNER_MODEL_ID", GLOBAL_MODEL_ID)

REPLY_MODEL_API_KEY = os.getenv("REPLY_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
REPLY_MODEL_BASE_URL = os.getenv("REPLY_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
REPLY_MODEL_ID = os.getenv("REPLY_MODEL_ID", GLOBAL_MODEL_ID)

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_NO_COLOR = os.getenv("LOG_NO_COLOR", "0") in ("1", "true", "True")
LOG_FILE = os.getenv("LOG_FILE", "")

# --- 搜索屏蔽城市列表 ---
# 逗号分隔，通过环境变量 BLOCKED_CITIES 覆盖
_DEFAULT_BLOCKED_CITIES = {"东京", "東京", "Tokyo", "大阪", "Osaka", "大阪市", "京都", "Kyoto", "名古屋", "Nagoya", "福岡", "Fukuoka"}
_env_cities = os.getenv("BLOCKED_CITIES", "")
BLOCKED_CITIES = set(c.strip() for c in _env_cities.split(",") if c.strip()) if _env_cities else _DEFAULT_BLOCKED_CITIES

# --- 维度中文标签 ---
DIM_LABELS = {
    "destination": "目的地",
    "accommodation": "住宿",
    "dining": "餐饮",
    "attraction": "景点",
    "shopping": "购物",
    "transportation": "交通",
    "weather": "天气",
    "policy": "政策",
    "general": "综合",
}
