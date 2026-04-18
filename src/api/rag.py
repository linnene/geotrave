"""
RAG API Module: Management endpoints for the vector database.

Provides interfaces for document ingestion, file uploads, and manual search tests.

Parent Module: src.api
Dependencies: fastapi, langchain_text_splitters, database.vector_db, api.schema, utils.logger
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Dict, Any

from utils.logger import logger
from api.schema import InsertRequest, SearchRequest, SearchResponse, SearchResult
from database.vector_db import add_documents_to_db, search_similar_documents, get_document_count

router = APIRouter(prefix="/rag", tags=["RAG Database"])

@router.post("/search/", response_model=SearchResponse)
async def search_rag_data(request: SearchRequest):
    """
    Search endpoint for manual verification of vector database content.
    """
    logger.debug(f"[RAG API] Search query: {request.query} (k={request.k})")
    try:
        # Fixed: search_similar_documents is an async function, must be awaited.
        results = await search_similar_documents(query=request.query, k=request.k)
        if not results:
            return SearchResponse(message="No relevant content found in database.", results=[])
        
        # Transform LangChain documents to serializable search results
        data = [
            SearchResult(content=doc.page_content, metadata=doc.metadata) 
            for doc in results
        ]
        return SearchResponse(results=data)
    except Exception as e:
        logger.error(f"[RAG API] Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database retrieval failure: {str(e)}")

@router.get("/stats/")
async def get_rag_stats():
    """
    Statistics endpoint to check total indexed document count.
    """
    try:
        count = get_document_count()
        logger.debug(f"[RAG API] Index count requested: {count}")
        return {"status": "success", "document_count": count}
    except Exception as e:
        logger.error(f"[RAG API] Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")

@router.post("/insert/")
async def insert_rag_data(request: InsertRequest):
    """
    Direct endpoint for inserting batches of text documents.
    """
    logger.info(f"[RAG API] Batch insert started: {len(request.documents)} items.")
    if not request.documents:
        raise HTTPException(status_code=400, detail="Document list cannot be empty.")
    
    docs = [item.content for item in request.documents]
    metadatas = [item.metadata for item in request.documents]
    
    try:
        add_documents_to_db(docs=docs, metadatas=metadatas)
        return {"status": "success", "message": f"Successfully inserted {len(docs)} documents."}
    except Exception as e:
        logger.error(f"[RAG API] Insert error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database write failure: {str(e)}")

@router.post("/upload/")
async def upload_file_to_rag(file: UploadFile = File(...)):
    """
    Upload and index .txt files via chunking and embedding.
    """
    logger.info(f"[RAG API] Processing file upload: {file.filename}")
    
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are currently supported.")
    
    content_bytes = await file.read()
    try:
        text_content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding must be UTF-8.")
    
    # Text split strategy: 1000 char chunks with overlap to preserve context
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )
    
    chunks = text_splitter.split_text(text_content)
    logger.info(f"[RAG API] File split into {len(chunks)} chunks.")
    
    try:
        # Attach source metadata to each chunk
        metadatas = [
            {"source": file.filename, "chunk_index": i} 
            for i in range(len(chunks))
        ]
        
        add_documents_to_db(docs=chunks, metadatas=metadatas)
        return {
            "status": "success", 
            "message": f"File '{file.filename}' processed and indexed into {len(chunks)} chunks."
        }
    except Exception as e:
        logger.error(f"[RAG API] Upload ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database write failure: {str(e)}")
