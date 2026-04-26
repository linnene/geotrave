"""
Module: src.database.vector_db.manager
Responsibility: Manages the local Chroma vector database instance and its directory.
Parent Module: src.database.vector_db
Dependencies: os, langchain_chroma, src.utils, src.database.vector_db.provider

Handles the lazy initialization and persistence logic of the Chroma repository.
"""

import os
from langchain_chroma import Chroma

from src.utils import config, logger
from .provider import EmbeddingsProvider

class VectorDBManager:
    """
    Manages the lifecycle of the Chroma vector database instance.
    Ensures the database directory exists and prevents redundant initializations.
    """
    
    def __init__(self, collection_name: str = "geotrave_guides"):
        """
        Initialize the VectorDBManager.
        
        Args:
            collection_name (str): The name of the ChromaDB collection to use.
        """
        self.collection_name = collection_name
        self._store = None
        self._embeddings = EmbeddingsProvider.get_embeddings()

    @property
    def store(self) -> Chroma:
        """
        Retrieve or initialize the shared ChromaDB Vector Store lazily.
        
        Returns:
            Chroma: The initialized vector store instance.
            
        Raises:
            RuntimeError: If the embeddings model failed to initialize.
        """
        if self._store is None:
            if self._embeddings is None:
                logger.error("[Manager] Cannot initialize Chroma: Embeddings model is None.")
                raise RuntimeError("Embeddings model initialization failed.")
            
            os.makedirs(config.CHROMA_DB_DIR, exist_ok=True)
            logger.debug(f"[Manager] Initializing ChromaDB at {config.CHROMA_DB_DIR}")
            
            self._store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self._embeddings,
                persist_directory=config.CHROMA_DB_DIR
            )
        return self._store