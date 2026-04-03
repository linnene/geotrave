import fastapi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.logger import logger
from .schema import InsertRequest, SearchRequest
from database.vector_db import add_documents_to_db, search_similar_documents, get_document_count

router = fastapi.APIRouter(prefix="/rag", tags=["RAG Database"])


@router.post("/search/")
async def search_rag_data(request: SearchRequest):
    """
    快速的文本检索测试，用于验证 ChromaDB 内容写入
    """
    logger.info(f"[RAG API] Search query: {request.query}")
    try:
        results = search_similar_documents(query=request.query, k=request.k)
        if not results:
            return {"status": "success", "message": "库中未找到相关内容", "results": []}
        
        # 将结构化的 Retrieval 结果转换输出
        data = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in results
        ]
        return {"status": "success", "results": data}
    except Exception as e:
        logger.error(f"[RAG API] Search error: {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库检索异常: {str(e)}")


@router.get("/stats/")
async def get_rag_stats():
    """
    检查当前 ChromaDB 中存储了多少条文档，作为验证是否写入成功的依据。
    """
    try:
        count = get_document_count()
        logger.info(f"[RAG API] DB Stats count: {count}")
        return {"status": "success", "document_count": count}
    except Exception as e:
        logger.error(f"[RAG API] Stats error: {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"检查状态失败: {str(e)}")


@router.post("/insert/")
async def insert_rag_data(request: InsertRequest):
    """
    接收文本和元数据，插入 ChromaDB 供 GeoTrave 检索。
    """
    logger.info(f"[RAG API] Insert request received, count: {len(request.documents)}")
    if not request.documents:
        raise fastapi.HTTPException(status_code=400, detail="文档列表不能为空")
    
    docs = [item.content for item in request.documents]
    metadatas = [item.metadata for item in request.documents]
    
    try:
        add_documents_to_db(docs=docs, metadatas=metadatas)
        logger.info("[RAG API] Insert success.")
        return {"status": "success", "message": f"成功插入 {len(docs)} 条记录"}
    except Exception as e:
        logger.error(f"[RAG API] Insert error: {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库写入异常: {str(e)}")


@router.post("/upload/")
async def upload_file_to_rag(file: fastapi.UploadFile = fastapi.File(...)):
    """
    通过上传文件( 支持 .txt )来将内容写入 ChromaDB 供 RAG 检索。
    """
    logger.info(f"[RAG API] Upload file received: {file.filename}")
    
    if not file.filename.endswith(".txt"): # type: ignore
        raise fastapi.HTTPException(status_code=400, detail="目前仅支持上传 .txt 文件。")
    
    content_bytes = await file.read()
    try:
        text_content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise fastapi.HTTPException(status_code=400, detail="File需要是 UTF-8 编码。")
    
    # LangChain Chunking
    # 1000 字符分块，200 字符重叠 (防止断句断在关键信息中间)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]
    )
    
    chunks = text_splitter.split_text(text_content)
    logger.info(f"[RAG API] File '{file.filename}' split into {len(chunks)} chunks.")
    
    try:
        # 为每个 Chunk 打上元数据标记
        metadatas = [
            {"source": file.filename, "chunk_index": i} 
            for i in range(len(chunks))
        ]
        
        add_documents_to_db(docs=chunks, metadatas=metadatas)
        logger.info(f"[RAG API] Upload success. Chunk count: {len(chunks)}")
        return {
            "status": "success", 
            "message": f"成功读取并切分为 {len(chunks)} 个分块并存入向量库。"
        }
    except Exception as e:
        logger.error(f"[RAG API] Upload error: {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库写入异常: {str(e)}")