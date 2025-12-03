from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image
import easyocr
from langchain_huggingface import HuggingFaceEmbeddings
import os
from langchain_core.documents import Document
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from openai import OpenAI
from pymongo import MongoClient
import json

load_dotenv()

def extractText(file_path,file_extension,file_name):
    QDRANT_URL = os.getenv("VECTORDB_URL", "http://localhost:6333")
    documents = []
    extracted_text =""
    if file_extension == "pdf":
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        extracted_text = "\n".join([d.page_content for d in docs])
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

    uri = os.getenv("DATABASE_URL")
    mongoClient = MongoClient(uri)

    try:   
        client = OpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai"
        )
        
        SYSTEM_PROMPT = """
            You are an AI assistant that is has a task to extract the medical data from the field 
            You need to extract all the medical report information from the uploaded PDF,Image,Text from the user

            Always output the valid json with this fields:
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

            Rules :
            - If the value is missing in the report keep it null
            - Do not hallucinate the values if the values is not clear write null
            - Convert the units to basic numeric format
            - Extract from the reports provided in the reports
            - Do not include the text outside of the JSON
            - if any additional important information add it in the paramter additional_notes which is a string 
            - Don't change the parameters and follow the rules strictly

            Example :
            Q: Ouput of the Medical Report uploaded by the user :
            A : 
                {
                    "blood_sugar_fasting": 98,
                    "blood_sugar_pp": 132,
                    "blood_pressure_systolic": 120,
                    "blood_pressure_diastolic": 80,
                    "hemoglobin": 14.2,
                    "rbc": 4.8,
                    "wbc": 6200,
                    "platelets": 210000,
                    "cholesterol_total": 176,
                    "hdl": 48,
                    "ldl": 102,
                    "triglycerides": 150,
                    "creatinine": 1.0,
                    "sgot": 32,
                    "sgpt": 30,
                    "tsh": 2.1,
                    "additional_notes": "Report indicates normal levels."
                }

    """

        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":extracted_text}
            ],
        )

        print(response)

        parsed_result = json.loads((response.choices[0].message.content).strip())

        database = mongoClient["health"]
        reports = database["Sources"]

        reports.insert_one({
            "file_name": file_name,
            "file_type": file_extension,
            "raw_text": extracted_text,
            "parsed_data": parsed_result
        })


        print("Saved on MongoDB ☑️")
    except Exception as e:
        raise Exception("Unable to find the document due to the following error: ", e)
    finally:
        mongoClient.close()
    

