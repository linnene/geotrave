from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class FetchError(Exception):
    """Raised by ContentFetcher methods to carry structured error metadata."""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class CrawlResult(BaseModel):
    """Standardized output for all crawling operations."""
    url: str
    title: Optional[str] = None
    content: Optional[str] = Field(None, description="Cleaned markdown content")
    status: str = Field(..., description="success | error | no_content_found")
    mode: str = Field(..., description="fast | deep")
    error_code: Optional[str] = Field(
        None, description="timeout | blocked | http_4xx | http_5xx | connection | empty_or_short | unknown"
    )
    error_message: Optional[str] = Field(None, description="Human-readable error detail")
    metadata: Dict[str, Any] = Field(default_factory=dict)
