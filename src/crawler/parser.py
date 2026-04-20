import trafilatura
from typing import Optional, Tuple
from readability import Document

class ContentParser:
    """Handles the extraction and cleaning of content from raw HTML."""
    
    @staticmethod
    def clean_with_trafilatura(html: str) -> Optional[str]:
        """High-precision extraction with Trafilatura."""
        return trafilatura.extract(
            html, 
            output_format='markdown',
            include_links=True,
            include_tables=True
        )

    @staticmethod
    def clean_with_readability(html: str) -> Tuple[Optional[str], Optional[str]]:
        """High-recall fallback with Readability-lxml."""
        try:
            doc = Document(html)
            title = doc.title()
            summary = doc.summary()
            # Feed readablity output back to trafilatura for cleaner markdown
            cleaned = trafilatura.extract(summary, output_format='markdown')
            return title, cleaned
        except Exception:
            return None, None

    def process_extraction(self, html: str) -> Tuple[Optional[str], Optional[str]]:
        """Runs the cleaning pipeline and returns (title, content)."""
        # 1. Primary: Trafilatura
        extracted = self.clean_with_trafilatura(html)
        
        # 2. Heuristic: If content is too thin, use Readability fallback
        if not extracted or len(extracted.strip()) < 300:
            title, read_extracted = self.clean_with_readability(html)
            if read_extracted:
                return title, read_extracted
        
        # Extract title from HTML if not extracted by readability
        doc_metadata = Document(html)
        return doc_metadata.title(), extracted

