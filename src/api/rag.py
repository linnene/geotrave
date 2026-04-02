import fastapi
from utils.logger import logger
from .schema import InsertRequest, SearchRequest
from database.vector_db import add_documents_to_db, search_similar_documents, get_document_count

router = fastapi.APIRouter(prefix="/rag", tags=["RAG Database"])


@router.post("/search/")
async def search_rag_data(request: SearchRequest):
    """
    快速的文本检索测试，用于验证 ChromaDB 内容写入
    """
    logger.info(f"API: 测试搜寻 RAG 库，关键字: {request.query}")
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
        logger.error(f"API: 检索 RAG 异常 - {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库检索异常: {str(e)}")


@router.get("/stats/")
async def get_rag_stats():
    """
    检查当前 ChromaDB 中存储了多少条文档，作为验证是否写入成功的依据。
    """
    try:
        count = get_document_count()
        logger.info(f"API: 检查 RAG 知识库，目前存在 {count} 个 Document 分块。")
        return {"status": "success", "document_count": count}
    except Exception as e:
        logger.error(f"API: 检查 RAG 状态异常 - {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"检查状态失败: {str(e)}")


@router.post("/insert/")
async def insert_rag_data(request: InsertRequest):
    """
    接收文本和元数据，插入 ChromaDB 供 GeoTrave 检索。
    """
    logger.info(f"API: 接收到 {len(request.documents)} 条 RAG 写入请求。")
    if not request.documents:
        raise fastapi.HTTPException(status_code=400, detail="文档列表不能为空")
    
    docs = [item.content for item in request.documents]
    metadatas = [item.metadata for item in request.documents]
    
    try:
        add_documents_to_db(docs=docs, metadatas=metadatas)
        logger.info("API: RAG 数据写入 ChromaDB 成功！")
        return {"status": "success", "message": f"成功插入 {len(docs)} 条记录"}
    except Exception as e:
        logger.error(f"API: 插入 RAG 数据失败 - {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库写入异常: {str(e)}")


@router.post("/upload/")
async def upload_file_to_rag(file: fastapi.UploadFile = fastapi.File(...)):
    """
    通过上传文件（支持 .txt）来将内容写入 ChromaDB 供 RAG 检索。
    """
    logger.info(f"API: 接收到文件上传请求，文件名: {file.filename}")
    
    if not file.filename.endswith(".txt"): # type: ignore
        # 暂时只用基础演示 txt。如需 pdf, 可引入 PyPDFLoader + pypdf 或 pdfplumber 库
        raise fastapi.HTTPException(status_code=400, detail="目前仅支持上传 .txt 文件。")
    
    content_bytes = await file.read()
    try:
        text_content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise fastapi.HTTPException(status_code=400, detail="文件必须是 UTF-8 编码。")
    
    # 作为整块长文输入（实际工业需要分块 Chunk，这里简单演示）
    try:
        metadata = {"source": file.filename}
        add_documents_to_db(docs=[text_content], metadatas=[metadata])
        logger.info(f"API: 文件 '{file.filename}' 内容已成功写入 ChromaDB！")
        return {"status": "success", "message": f"成功读取并插入文件 '{file.filename}' 的内容。"}
    except Exception as e:
        logger.error(f"API: 文件RAG写入异常 - {str(e)}")
        raise fastapi.HTTPException(status_code=500, detail=f"数据库写入异常: {str(e)}")

