"""
Config Module: Global configuration management for GeoTrave.

Handles environment variables, LLM parameters, and system-wide settings.

Parent Module: src.utils
Dependencies: python-dotenv
"""

import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# --- Global Fallback LLM Settings ---
GLOBAL_MODEL_API_KEY = os.getenv("GLOBAL_MODEL_API_KEY", "")
GLOBAL_MODEL_BASE_URL = os.getenv("GLOBAL_MODEL_BASE_URL", "")
GLOBAL_MODEL_ID = os.getenv("GLOBAL_MODEL_ID", "")

# --- Node-Specific LLM Configuration ---
# Analyzer Node
ANALYZER_MODEL_API_KEY = os.getenv("ANALYZER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
ANALYZER_MODEL_BASE_URL = os.getenv("ANALYZER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
ANALYZER_MODEL_ID = os.getenv("ANALYZER_MODEL_ID", GLOBAL_MODEL_ID)

# Researcher Node
RESEARCHER_MODEL_API_KEY = os.getenv("RESEARCHER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
RESEARCHER_MODEL_BASE_URL = os.getenv("RESEARCHER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
RESEARCHER_MODEL_ID = os.getenv("RESEARCHER_MODEL_ID", GLOBAL_MODEL_ID)

# Router Node
ROUTER_MODEL_API_KEY = os.getenv("ROUTER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
ROUTER_MODEL_BASE_URL = os.getenv("ROUTER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
ROUTER_MODEL_ID = os.getenv("ROUTER_MODEL_ID", GLOBAL_MODEL_ID)

# Planner Node
PLANNER_MODEL_API_KEY = os.getenv("PLANNER_MODEL_API_KEY", GLOBAL_MODEL_API_KEY)
PLANNER_MODEL_BASE_URL = os.getenv("PLANNER_MODEL_BASE_URL", GLOBAL_MODEL_BASE_URL)
PLANNER_MODEL_ID = os.getenv("PLANNER_MODEL_ID", GLOBAL_MODEL_ID)

# --- Embedding & Vector DB ---
EMBEDDING_MODEL_API_KEY = os.getenv("EMBEDDING_MODEL_API_KEY", "")
EMBEDDING_MODEL_BASE_URL = os.getenv("EMBEDDING_MODEL_BASE_URL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./data/chroma")
DB_TIMEOUT = 60

# --- General Agent Parameters ---
PLANNING_TEMPERATURE = 0.7
MAX_TOKENS = 4096
LLM_TIMEOUT = 60

# --- System & Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
