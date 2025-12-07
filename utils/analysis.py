from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from pymongo import MongoClient
import json
from qdrant_client.models import Filter, FieldCondition, MatchValue,PayloadSchemaType
from qdrant_client.http.exceptions import UnexpectedResponse
import asyncio

load_dotenv()

async def analysis(input,username):
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

    try:
        print("Started")
        uri = os.getenv("DATABASE_URL")
        mongoClient = MongoClient(uri)

        database = mongoClient["health"]
        reports = database["Sources"]

        query_filter = {"user":username}
        update_operation = {"$set":
            {"symptoms":input}                  
        }

        result = reports.update_one(query_filter, update_operation)
        print("Ended")
    except Exception as e:
        raise Exception("The following error occurred: ", e)
    finally:
        if 'mongoClient' in locals():
            mongoClient.close()

    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

    QDRANT_URL = os.getenv("VECTORDB_URL","http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY or None,   # works for both local (no key) and cloud
    )

    # ------------------------------------------------------------------
    #  👉 QDRANT INDEX FIX (Added Here)
    #  This is the necessary setup to resolve the "Index required" error.
    #  It uses error handling to safely skip if the index already exists.
    # ------------------------------------------------------------------
    try:
        qdrant_client.create_payload_index(
            collection_name="ai_health_analysis",
            field_name="user",
            field_schema=PayloadSchemaType.KEYWORD,
            # wait=True is useful to ensure the index is ready before proceeding
            wait=True 
        )
        print("'user' keyword index created successfully.")
    except UnexpectedResponse as e:
        error_content = str(e).lower()
        if "already exists" in error_content or "bad request" in error_content:
            print("Keyword index already exists for 'user'. Skipping creation.")
        else:
            print(f"Failed to create index with an unexpected error: {e}")
    except Exception as e:
        print(f"A general exception occurred during index creation: {e}")
    # ------------------------------------------------------------------

    vector_db = QdrantVectorStore(
        client=qdrant_client,
        embedding=embedding,
        collection_name="ai_health_analysis"
    )

    print("Vector DB Semantic Search Started")

    filter =Filter(
        must=[
            FieldCondition(
                key="user",
                match=MatchValue(value=username)
            )
        ]
    )

    search_results = await  vector_db.similarity_search(query=input,k=5,filter=filter)

    print("Vector DB Semantic Search Ended")

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

    response = await client.chat.completions.create(
        model="nvidia/nemotron-nano-12b-v2-vl:free",
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":input}
        ]
    )

    print("Response:",response)

    return response.choices[0].message.content

async def generateSuggestions(username):
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

    uri = os.getenv("DATABASE_URL")
    mongoClient = MongoClient(uri)

    try:
        database = mongoClient["health"]
        reports = database["Sources"]
        results = reports.find({"user":username})
        raw_text = ""
        parsed_data= ""
        symptoms = ""
        for report in results:
            raw_text = report.get("raw_text")
            parsed_data = report.get("parsed_data")
            symptoms = report.get("symptoms", None) 

        SYSTEM_PROMPT = """
            You are an AI assistant who is tasked to provide suggestion to the concerned user regarding their medical reports , symptoms and medical history

            User would provide you the context in the below form : 
            {
                "text":"Medical History of the user in string",
                "medical_params":
                                {
                    "blood_sugar_fasting": null or number,
                    "blood_sugar_pp": null or number,
                    "blood_pressure_systolic": null or number,
                    "blood_pressure_diastolic": null or number,
                    "hemoglobin": null or number,
                    "rbc": null or number,
                    "wbc": null or number,
                    "platelets": null or number,
                    "cholesterol_total": null or number,
                    "hdl": null or number,
                    "ldl": null or number,
                    "triglycerides": null or number,
                    "creatinine": null or number,
                    "sgot": null or number,
                    "sgpt": null or number,
                    "tsh": null or number,
                    "additional_notes": "string"
                }
                "symptoms":string
            } 

            Using the context passed provide the most suitable and appropraite suggestions that aligns with the users health care and well being

            Rules :
            - Do not hallucinate and advise the user for something we are not certain to advise
            - Keep the tone of the message light and straight
            - The suggestion should be generaed from the context provided only
        """

        information = json.dumps({
            "text":raw_text,
            "medical_params":parsed_data,
            "symptoms":symptoms
        })

        print("Before Response",information)
        response = await client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages = [
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":information}
            ]
        )

        return response.choices[0].message.content
    finally:
        mongoClient.close()



