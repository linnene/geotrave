"""
Module: src.database.vector_db.provider
Responsibility: Manages the initialization of embedding endpoints for RAG operations.
Parent Module: src.database.vector_db
Dependencies: pydantic, langchain_google_genai, src.utils

Provides the foundational embedding models required by the vector database.
Utilizes Google Generative AI for embeddings.
"""

from typing import Optional
from pydantic import SecretStr
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.utils import config, logger

class EmbeddingsProvider:
    """
    Provides the initialization and instance retrieval for Embeddings models.
    """
    
    @staticmethod
    def get_embeddings() -> Optional[GoogleGenerativeAIEmbeddings]:
        """
        Initialize and return the Google Generative AI Embeddings model.
        
        Returns:
            Optional[GoogleGenerativeAIEmbeddings]: The initialized embeddings model, 
            or None if initialization fails.
        """
        try:
            return GoogleGenerativeAIEmbeddings(
                model=config.EMBEDDING_MODEL,
                api_key=SecretStr(config.EMBEDDING_MODEL_API_KEY or "dummy_api_key_for_testing"),
            )
        except Exception as e:
            logger.error(f"[Provider] Failed to initialize Google Embeddings: {e}")
            return None