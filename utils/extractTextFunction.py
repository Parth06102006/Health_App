from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image
import easyocr
from langchain_huggingface import HuggingFaceEmbeddings
import os
from langchain_core.documents import Document
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore

load_dotenv()

def extractText(file_path,file_extension,file_name):
    QDRANT_URL = os.getenv("VECTORDB_URL", "http://localhost:6333")
    documents = []
    if file_extension == "pdf":
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, 
        )

        documents = text_splitter.split_documents(docs)

    elif file_extension in ["jpg", "jpeg", "png"]:
        reader = easyocr.Reader(['en'])
        results = reader.readtext(file_path,detail=0)
        extracted_text = "\n".join(results)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=80, 
        )

        chunks = text_splitter.split_text(extracted_text)

        documents = [
            Document(page_content=chunk, metadata={"source": file_name})
            for chunk in chunks
        ]

    else :
        raise Exception("File Type not Supported")
    
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

    print(QDRANT_URL)
    QdrantVectorStore.from_documents(
        documents=documents,
        embedding=embedding,
        url=QDRANT_URL,
        collection_name="ai_health_analysis",
        force_recreate=False
    )

    print("Indexing Done")
    
    

    
    
        
