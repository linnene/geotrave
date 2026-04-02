import os
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
    api_key = SecretStr(EMBEDDING_MODEL_API_KEY),
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

def search_similar_documents(query: str, k: int = 3):
    """
    search similar txts from vector db
    """
    vector_store = get_vector_store()
    results = vector_store.similarity_search(query, k=k)
    return results
