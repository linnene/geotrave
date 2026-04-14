import os
from functools import lru_cache
from pydantic import SecretStr
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from utils.config import(
    CHROMA_DB_DIR, 
    EMBEDDING_MODEL, 
    EMBEDDING_MODEL_API_KEY
) 

# INIT Google`s Embedding MODEL
embeddings = GoogleGenerativeAIEmbeddings(
    model = EMBEDDING_MODEL,
    api_key = SecretStr(EMBEDDING_MODEL_API_KEY or "dummy_api_key_for_testing"),
)

def get_vector_store(collection_name: str = "geotrave_guides"):
    """
    Shared ChromaDB Vector Store 
    """
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)
    
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    
    return vector_store

def add_documents_to_db(docs: list[str], metadatas: list[dict]):
    """
    insert txts into vector db with metadata
    """
    vector_store = get_vector_store()
    vector_store.add_texts(texts=docs, metadatas=metadatas)    

#TODO：完善RAG返回缓存逻辑
@lru_cache(maxsize=100)
def _getCachedSearchResults(query: str, k: int):
    """
    内部缓存函数，利用 lru_cache 缓存检索出来的文档对象
    """
    vector_store = get_vector_store()
    results = vector_store.similarity_search(query, k=k)
    return results

#TODO：完善RAG检索接口，增加检索参数query,异步查询逻辑完善
async def search_similar_documents(query: str, k: int = 3):
    """
    search similar txts from vector db asynchronously
    """
    import asyncio
    # 利用 to_thread 将阻塞的 requests API （Embedding 动作等）丢到后台真线程里执行
    # 如果 query 和 k 相同，也照样可以通过被 lru_cache 装饰的底层函数利用到内存缓存
    results = await asyncio.to_thread(_getCachedSearchResults, query, k)
    return results


def get_document_count() -> int:
    """
    获取 ChromaDB 集合中的文档总数
    """
    vector_store = get_vector_store()
    # 访问底层 chroma client 的集合计数
    try:
        return vector_store._collection.count()
    except Exception:
        return 0

