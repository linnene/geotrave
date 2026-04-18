"""
API Schema Module: Data models for REST API requests and responses.

Defines Pydantic models for validated data exchange.

Parent Module: src.api
Dependencies: pydantic
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Chat API Models ---
class ChatRequest(BaseModel):
    """Payload for user chat messages."""
    message: str = Field(..., min_length=1, description="Content of the user message")
    session_id: str = Field(default="default_session", description="Unique session ID for conversation history persistence")

class ChatResponse(BaseModel):
    """Response returned after processing a chat request."""
    reply: str
    session_id: str
    status: str = "success"

# --- RAG API Models ---
class DocumentItem(BaseModel):
    """A single document unit for RAG ingestion."""
    content: str = Field(..., description="Text content to be indexed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the content")

class InsertRequest(BaseModel):
    """Batch insertion request for RAG."""
    documents: List[DocumentItem]

class SearchRequest(BaseModel):
    """Query model for searching the vector database."""
    query: str = Field(..., description="Query string for semantic search")
    k: int = Field(default=3, description="Number of top results to return")

class SearchResult(BaseModel):
    """Individual result from a vector search."""
    content: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    """Standardized search response wrapper."""
    status: str = "success"
    results: List[SearchResult]
    message: Optional[str] = None
