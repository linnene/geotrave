"""
Module: src.api.rag
Responsibility: CRUD operations and file ingestion for the ChromaDB-backed Knowledge Base (RAG).
Parent Module: src.api
Dependencies: fastapi, langchain_text_splitters, src.database.vector_db, src.api.schema, src.utils

This module provides endpoints for:
1. Similarity search (RAG verification)
2. Database statistics
3. Manual document insertion
4. .txt file upload and chunking
"""

import fastapi
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.api.schema import InsertRequest, SearchRequest
from src.database.vector_db import add_documents_to_db, search_similar_documents, get_document_count
from src.utils import logger

router = fastapi.APIRouter()

@router.post("/search/")
async def search_rag_data(request: SearchRequest):
    """
    Retrieves similar documents from the vector database for testing or verification.
    """
    logger.debug(f"[RAG API] Search query: {request.query}")
    try:
        # Calls the optimized async search with internal thread pooling
        results = await search_similar_documents(query=request.query, k=request.k)
        
        if not results:
            return {"status": "success", "message": "库中未找到相关内容", "results": []}
        
        # Transform structured Retrieval results for API consumption
        data = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in results
        ]
        return {"status": "success", "results": data}
    except Exception as e:
        logger.error(f"[RAG API] Search error: {e}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库检索异常: {str(e)}")

@router.get("/stats/")
async def get_rag_stats():
    """
    Returns the total count of documents in the ChromaDB collection.
    """
    try:
        count = get_document_count()
        logger.debug(f"[RAG API] DB Stats count: {count}")
        return {"status": "success", "document_count": count}
    except Exception as e:
        logger.error(f"[RAG API] Stats error: {e}")
        raise fastapi.HTTPException(status_code=500, detail=f"检查状态失败: {str(e)}")

@router.post("/insert/")
async def insert_rag_data(request: InsertRequest):
    """
    Inserts a list of documents and metadata manually into the database.
    """
    logger.info(f"[RAG API] Manual insert requested for {len(request.documents)} items")
    if not request.documents:
        raise fastapi.HTTPException(status_code=400, detail="文档列表不能为空")
    
    docs = [item.content for item in request.documents]
    metadatas = [item.metadata for item in request.documents]
    
    try:
        # add_documents_to_db remains synchronous as it usually happens during startup or ingestion
        add_documents_to_db(docs=docs, metadatas=metadatas)
        logger.info("[RAG API] Manual insert success.")
        return {"status": "success", "message": f"成功插入 {len(docs)} 条记录"}
    except Exception as e:
        logger.error(f"[RAG API] Manual insert error: {e}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库写入异常: {str(e)}")

@router.post("/upload/")
async def upload_file_to_rag(file: fastapi.UploadFile = fastapi.File(...)):
    """
    Handles file uploads (.txt, .md), performs chunking, and stores results in ChromaDB.
    """
    logger.info(f"[RAG API] Upload file received: {file.filename}")
    
    # Check for supported extensions: .txt and .md
    supported_extensions = (".txt", ".md")
    if not (file.filename and file.filename.lower().endswith(supported_extensions)):
        raise fastapi.HTTPException(status_code=400, detail="目前仅支持上传 .txt 或 .md 文件。")
    
    content_bytes = await file.read()
    try:
        text_content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise fastapi.HTTPException(status_code=400, detail="文件编码错误，请确保使用 UTF-8 编码。")
    
    # Strategy: Markdown files often have specific structures. 
    # For now, we use RecursiveCharacterTextSplitter with Markdown-friendly separators.
    # We can also add "#" to separators to respect header boundaries.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", "###", "##", "#", "。", "！", "？", " ", ""]
    )
    
    chunks = text_splitter.split_text(text_content)
    logger.info(f"[RAG API] File '{file.filename}' split into {len(chunks)} chunks.")
    
    try:
        # Prepare metadata for each chunk
        metadatas = [
            {"source": file.filename, "chunk_index": i} 
            for i in range(len(chunks))
        ]
        
        add_documents_to_db(docs=chunks, metadatas=metadatas)
        logger.info(f"[RAG API] Upload ingestion success: {file.filename}")
        
        return {
            "status": "success", 
            "message": f"成功读取并切分为 {len(chunks)} 个分块并存入向量库。"
        }
    except Exception as e:
        logger.error(f"[RAG API] Upload processing error: {e}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库写入异常: {str(e)}")
