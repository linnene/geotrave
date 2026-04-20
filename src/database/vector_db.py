"""
Module: src.database.vector_db
Responsibility: Manages the local Chroma vector database and embedding endpoints for RAG operations.
Parent Module: src.database
Dependencies: os, asyncio, pydantic, langchain_chroma, langchain_google_genai, src.utils

Provides asynchronous document retrieval and synchronous document insertion.
Utilizes Google Generative AI for embeddings and a local Chroma repository for persistence.
"""

import os
import asyncio
from functools import lru_cache
from typing import List, Dict, Any

from pydantic import SecretStr
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Standardized unidirectional import from the configuration facade
from src.utils import config

# Initialize Google's Embedding Model globally.
embeddings = GoogleGenerativeAIEmbeddings(
    model=config.EMBEDDING_MODEL,
    api_key=SecretStr(config.EMBEDDING_MODEL_API_KEY or "dummy_api_key_for_testing"),
)

def get_vector_store(collection_name: str = "geotrave_guides") -> Chroma:
    """
    Retrieve or initialize the shared ChromaDB Vector Store.
    
    Args:
        collection_name (str): The namespace identifier for the collection.
        
    Returns:
        Chroma: The instantiated vector store handler.
    """
    os.makedirs(config.CHROMA_DB_DIR, exist_ok=True)
    
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=config.CHROMA_DB_DIR
    )
    
    return vector_store

def add_documents_to_db(docs: List[str], metadatas: List[Dict[str, Any]]) -> None:
    """
    Insert texts synchronously into the vector database with associated metadata.
    
    Args:
        docs (List[str]): List of textual documents to embed and store.
        metadatas (List[Dict[str, Any]]): Corresponding metadata payload for each document.
    """
    vector_store = get_vector_store()
    vector_store.add_texts(texts=docs, metadatas=metadatas)

@lru_cache(maxsize=100)
def _get_cached_search_results(query: str, k: int) -> List[Any]:
    """
    Internal synchronous search function leveraging LRU cache for identical queries.
    
    Args:
        query (str): The search query string.
        k (int): Result limit.
        
    Returns:
        List[Any]: A list of similar LangChain Document objects.
    """
    vector_store = get_vector_store()
    return vector_store.similarity_search(query, k=k)

async def search_similar_documents(query: str, k: int = 3) -> List[Any]:
    """
    Asynchronously search for similar texts from the vector database.
    Offloads the potentially blocking disk/network I/O to a background thread.
    
    Args:
        query (str): The targeted search string.
        k (int): Number of top documents to return. Default is 3.
        
    Returns:
        List[Any]: List of matching documents.
    """
    # Dispatch synchronous blocking embedding/retrieval call to a worker thread
    results = await asyncio.to_thread(_get_cached_search_results, query, k)
    return results

def get_document_count() -> int:
    """
    Retrieve the total number of documents currently stored in the collection.
    
    Returns:
        int: The aggregate count of documents, or 0 if uninitialized/errored.
    """
    vector_store = get_vector_store()
    try:
        # Access the private collection attribute defensively
        collection = getattr(vector_store, "_collection", None)
        if collection is not None:
            return collection.count()  # type: ignore
        return 0
    except Exception:
        return 0

