"""
Module: src.database.vector_db.service
Responsibility: Exposes CRUD operations for RAG operations (retrieval and insertion).
Parent Module: src.database.vector_db
Dependencies: asyncio, src.utils, src.database.vector_db.manager

Provides asynchronous document retrieval and synchronous document insertion.
Abstracts away the underlying database instance management from the business logic.
"""

import asyncio
from typing import List, Dict, Any

from src.utils import logger
from .manager import VectorDBManager

# Global instance for default operations
db_manager = VectorDBManager()

def add_documents_to_db(docs: List[str], metadatas: List[Dict[str, Any]]) -> None:
    """
    Insert texts synchronously into the vector database with associated metadata.
    
    Args:
        docs (List[str]): List of textual documents to embed and store.
        metadatas (List[Dict[str, Any]]): Corresponding metadata payload for each document.
    """
    try:
        db_manager.store.add_texts(texts=docs, metadatas=metadatas)
        logger.debug(f"[Service] Successfully added {len(docs)} documents to DB.")
    except Exception as e:
        logger.error(f"[Service] Error adding documents to DB: {e}")
        raise

async def search_similar_documents(query: str, k: int = 3) -> List[Any]:
    """
    Asynchronously search for similar texts from the vector database.
    Offloads the potentially blocking disk/network I/O to a background thread.
    
    Args:
        query (str): The targeted search string.
        k (int): Number of top documents to return. Default is 3.
        
    Returns:
        List[Any]: List of matching LangChain Document objects.
    """
    def _sync_search():
        logger.debug(f"[Service] Executing similarity search for query: '{query}'")
        return db_manager.store.similarity_search(query, k=k)
    
    return await asyncio.to_thread(_sync_search)

def get_document_count() -> int:
    """
    Retrieve the total number of documents currently stored in the collection.
    
    Returns:
        int: The aggregate count of documents, or 0 if uninitialized/errored.
    """
    try:
        collection = getattr(db_manager.store, "_collection", None)
        if collection is not None:
            return collection.count()  # type: ignore
        return 0
    except Exception as e:
        logger.warning(f"[Service] Failed to retrieve document count: {e}")
        return 0