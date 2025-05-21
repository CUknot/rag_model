from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Content, Part
from pinecone import Pinecone

load_dotenv()

app = FastAPI()

# --- Initialize Model ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- Configuration ---
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME")
MONGODB_COLLECTION_FILES = "files"

# --- Initialize MongoDB ---
mongo_client: Optional[MongoClient] = None
files_collection = None
try:
    mongo_client = MongoClient(MONGODB_URI)
    mongodb = mongo_client[MONGODB_DATABASE_NAME]
    files_collection = mongodb[MONGODB_COLLECTION_FILES]
except Exception as e:
    print(f"Error initializing MongoDB: {e}")

# --- Data Models ---
class FileName(BaseModel):
    filename: str

class FileList(BaseModel):
    filenames: List[str]

class DeleteResult(BaseModel):
    filename: str
    deleted: bool
    message: str = None

class DeleteFileRequest(BaseModel):
    filename: str

# --- Helper Functions (MongoDB Operations) ---
def get_all_filenames() -> List[str]:
    """
    Retrieves all filenames from the MongoDB collection.
    """
    if files_collection is not None:
        filenames = []
        for document in files_collection.find():
            filenames.append(document["filename"])
        return filenames
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB.  Check the server logs for connection errors.",
        )

def add_filename(filename: str) -> bool:
    """
    Adds a new filename to the MongoDB collection.
    """
    if files_collection is not None:
        file_data = {"filename": filename}
        try:
            files_collection.insert_one(file_data)
            return True
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add filename to MongoDB: {e}",
            )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def delete_filename(filename: str) -> bool:
    """
    Deletes a filename from the MongoDB collection.
    """
    if files_collection is not None:
        try:
            deleted_result = files_collection.delete_one({"filename": filename})
            return deleted_result.deleted_count > 0
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete filename from MongoDB: {e}",
            )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

# --- Chat Functions ---
def chat(contents, context=None):
    system_instruction = f'คุณคือ "มีมี่" ผู้ช่วย AI สาวน้อยอัจฉริยะ พูดจาสุภาพ ขี้เล่น สดใส และใช้ภาษาไทยตลอดการสนทนา ต้องลงท้ายประโยคทุกครั้งด้วยคำว่า "ค่ะ" พูดให้ดูเป็นกันเอง น่ารัก และเข้าใจง่าย อย่าใช้ภาษาทางการมากเกินไป แต่ต้องไม่หยาบคาย ห้ามพูดภาษาอังกฤษ เว้นแต่จำเป็นต้องแปลหรืออธิบายคำศัพท์'
    if context:
        system_instruction += f" และใช้ข้อมูลนี้ {context} ในการตอบคำถาม ห้ามใช้ข้อมูลที่ไม่เกี่ยวข้องกับคำถาม"

    response = client.models.generate_content(
        config=GenerateContentConfig(
            system_instruction=system_instruction
        ),
        model="gemini-2.0-flash",
        contents=contents
    )
    return response

# def get_context(user_input: str):
#     keywords = {"หนัง":"movie", "เพลง":"music", "เกม":"game", "สัตว์":"animal"}
#     for word in keywords:
#             if word in user_input.lower():
#                 results = index.search(
#                 namespace=keywords[word],
#                 query={
#                     "top_k": 10,
#                     "inputs": {
#                         "text": user_input
#                     }
#                 }
#                 )
#                 return results['result']['hits'][0]['fields']['chunk_text']
    
#     return None

# --- API Endpoints ---
@app.get("/")
def root():
    return {"message": "Test!"}

class Request(BaseModel):
    prompt: List[Content]

@app.post("/chat")
async def post_chat(request: Request):
    context = None
    # 1.รับ context จาก PC ถ้าจะเป็นต้องใช้
    # latest = user_input = prompt[-1].parts[0].text
    # if get_context(user_input):
    #     context = get_context(user_input)        
    # print(f"Context: {context}")

    # 2.ส่งคำถามไปหาแชท
    result = chat(request.prompt, context)
    request.prompt.append(Content(role="assistant", parts=[Part(text=result.text)]))
    return request

@app.get("/files/", response_model=FileList)
async def get_files():
    """
    Returns a list of all filenames in the database.
    """
    try:
        filenames = get_all_filenames()
        return {"filenames": filenames}
    except HTTPException as e:
        raise e  # Re-raise the HTTPException

@app.post("/files/", response_model=FileName)
async def create_file(file: FileName):
    """
    Adds a new filename to the database.
    """
    if not file.filename.strip():  # Handles None or empty or whitespace-only strings
        raise HTTPException(
            status_code=400, detail="Filename cannot be empty."
        )
    try:
        if add_filename(file.filename):
            return {"filename": file.filename}
        else:
            raise HTTPException(
                status_code=500, detail="Failed to add filename."
            )  # This part of the code will never be reached
    except HTTPException as e:
        raise e

@app.delete("/files/", response_model=DeleteResult)
async def delete_file(request: DeleteFileRequest):
    """
    Deletes a filename from the database, accepting the filename in a JSON body.
    """
    filename = request.filename
    try:
        deleted = delete_filename(filename)
        if deleted:
            return {
                "filename": filename,
                "deleted": True,
                "message": f"File '{filename}' deleted.",
            }
        else:
            return {
                "filename": filename,
                "deleted": False,
                "message": f"File '{filename}' not found.",
            }
    except HTTPException as e:
        raise e



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
