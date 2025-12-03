from openai import OpenAI
from dotenv import load_dotenv
import os
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

def analysis(input):
    print(os.getenv("OPENAI_API_KEY"))
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

    QDRANT_URL = os.getenv("VECTORDB_URL","http://localhost:6333")

    vector_db  =QdrantVectorStore.from_existing_collection(
        embedding=embedding,
        url=QDRANT_URL,
        collection_name="ai_health_analysis"
    )

    search_results = vector_db.similarity_search(query=input)

    context = "\n\n\n".join([
    f"Page Content : {result.page_content}\nFile Location: {result.metadata['source']}"
    for result in search_results
])

    SYSTEM_PROMPT = f"""
        You are a helpful AI assistant who has expertise in medical field and the main aim is to provide the most accurate disease from the context provided retrieved from the image and the pdf file

        You must answer based on the context provided and give the repsonse in the most professional and general manner to the user so that it is clear what is the probable cause of the disease and the probability of it 
        
        Extract key health indicators like \"sugar level , cholestrol , blood pressure etc.\"

        Context:{context}
    """

    response = client.chat.completions.create(
        model="nvidia/nemotron-nano-12b-v2-vl:free",
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":input}
        ]
    )

    print("Response:",response)

    return response.choices[0].message.content