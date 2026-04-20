from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CrawlResult(BaseModel):
    """Standardized output for all crawling operations."""
    url: str
    title: Optional[str] = None
    content: Optional[str] = Field(None, description="Cleaned markdown content")
    status: str = Field(..., description="success | error | no_content_found")
    mode: str = Field(..., description="fast | deep")
    metadata: Dict[str, Any] = Field(default_factory=dict)
