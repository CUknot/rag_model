from fastapi import FastAPI, HTTPException, Body, Query # Import Query for query parameters
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Content, Part

# Import the Pinecone functions, including the new delete_pinecone_index
from src.pinecone.main import (
    upload_text_to_pinecone, 
    get_pinecone_index_info, 
    delete_file_from_pinecone,
    delete_pinecone_index # NEW IMPORT
)

load_dotenv()

app = FastAPI()

# --- Configuration ---
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME")
MONGODB_COLLECTION_FILES = "files"

# --- Initialize Model ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# --- Initialize MongoDB ---
mongo_client: Optional[MongoClient] = None
files_collection = None
try:
    mongo_client = MongoClient(MONGODB_URI)
    mongodb = mongo_client[MONGODB_DATABASE_NAME]
    files_collection = mongodb[MONGODB_COLLECTION_FILES]
    print("MongoDB initialized successfully.")
except Exception as e:
    print(f"Error initializing MongoDB: {e}")
    # Consider raising an exception or having a health check if MongoDB is critical

# --- Data Models ---
class UploadFileRequest(BaseModel):
    filename: str
    text_content: str
    category: str # Added category for Pinecone namespace/metadata

class UploadFileResponse(BaseModel):
    filename: str
    num_chunks: int
    pinecone_status: str
    mongo_status: str

class FileRecord(BaseModel): # To represent file records from MongoDB
    filename: str
    num_chunks: int
    category: str 
    # Add other fields if your MongoDB document grows

class DeleteFileRequest(BaseModel):
    filename: str

class DeleteResult(BaseModel):
    filename: str
    deleted_mongo: bool
    deleted_pinecone: bool
    mongo_message: str = None
    pinecone_message: str = None

class PineconeIndexDeleteResponse(BaseModel): # NEW Pydantic Model for index deletion
    index_name: str
    deleted: bool
    message: str

# --- Helper Functions (MongoDB Operations) ---
def get_all_file_records() -> List[FileRecord]:
    """
    Retrieves all filenames and their chunk counts from the MongoDB collection.
    """
    if files_collection is not None:
        records = []
        for document in files_collection.find():
            records.append(FileRecord(
                filename=document.get("filename"),
                num_chunks=document.get("num_chunks", 0),
                category=document.get("category", "default")
            ))
        return records
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def get_file_record_from_mongo(filename: str) -> Optional[FileRecord]:
    """
    Retrieves a single file record by filename from MongoDB.
    """
    if files_collection is not None:
        document = files_collection.find_one({"filename": filename})
        if document:
            return FileRecord(
                filename=document.get("filename"),
                num_chunks=document.get("num_chunks", 0),
                category=document.get("category", "default")
            )
        return None
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )


def add_file_record(filename: str, num_chunks: int, category: str) -> bool:
    """
    Adds a new filename, its chunk count, and category to the MongoDB collection.
    """
    if files_collection is not None:
        file_data = {"filename": filename, "num_chunks": num_chunks, "category": category} 
        try:
            if files_collection.find_one({"filename": filename}):
                raise HTTPException(status_code=409, detail=f"Filename '{filename}' already exists in MongoDB.")
            
            files_collection.insert_one(file_data)
            return True
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add file record to MongoDB: {e}",
            )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def delete_file_record_from_mongo(filename: str) -> bool:
    """
    Deletes a filename record from the MongoDB collection.
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

# --- API Endpoints ---
@app.get("/files/", response_model=List[FileRecord])
async def get_files():
    """
    Returns a list of all filenames and their chunk counts in the database.
    """
    try:
        records = get_all_file_records()
        return records
    except HTTPException as e:
        raise e

@app.post("/upload-text/", response_model=UploadFileResponse)
async def upload_text_with_metadata(request: UploadFileRequest):
    """
    Uploads text content, splits it into chunks, sends to Pinecone,
    and records the filename and chunk count in MongoDB.
    """
    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")
    if not request.text_content.strip():
        raise HTTPException(status_code=400, detail="Text content cannot be empty.")
    if not request.category.strip():
        raise HTTPException(status_code=400, detail="Category cannot be empty.")

    pinecone_upload_successful = False
    num_chunks_uploaded = 0
    pinecone_message = "Pending"

    try:
        num_chunks_uploaded = upload_text_to_pinecone(
            filename=request.filename,
            text=request.text_content,
            category=request.category
        )
        pinecone_upload_successful = True
        pinecone_message = "Success"
    except Exception as e:
        pinecone_message = f"Pinecone upload failed: {e}"
        print(f"Error during Pinecone upload for '{request.filename}': {e}")
        raise HTTPException(status_code=500, detail=pinecone_message)

    mongo_record_successful = False
    mongo_message = "Pending"

    try:
        if add_file_record(request.filename, num_chunks_uploaded, request.category): 
            mongo_record_successful = True
            mongo_message = "Success"
        else:
            mongo_message = "Failed to add record to MongoDB after Pinecone upload."
    except HTTPException as e:
        mongo_message = f"MongoDB record failed: {e.detail}"
        print(f"Error during MongoDB record for '{request.filename}': {e.detail}")
        raise e
    except Exception as e:
        mongo_message = f"MongoDB record failed: {e}"
        print(f"Error during MongoDB record for '{request.filename}': {e}")
        raise HTTPException(status_code=500, detail=mongo_message)

    return UploadFileResponse(
        filename=request.filename,
        num_chunks=num_chunks_uploaded,
        pinecone_status=pinecone_message,
        mongo_status=mongo_message
    )

@app.delete("/files/", response_model=DeleteResult)
async def delete_file_and_vectors(request: DeleteFileRequest):
    """
    Deletes a filename record from MongoDB and its associated vectors from Pinecone.
    The num_chunks and category are fetched from MongoDB.
    """
    filename = request.filename
    
    mongo_deleted = False
    pinecone_deleted = False
    mongo_msg = "Pending"
    pinecone_msg = "Pending"
    
    file_record = get_file_record_from_mongo(filename)

    if not file_record:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in MongoDB.")
    
    num_chunks = file_record.num_chunks
    category = file_record.category

    try:
        pinecone_delete_result = delete_file_from_pinecone(filename, num_chunks, category)
        pinecone_deleted = pinecone_delete_result.get("deleted", False)
        pinecone_msg = pinecone_delete_result.get("message", "Unknown Pinecone deletion status.")
        if not pinecone_deleted:
            print(f"Warning: Pinecone deletion failed for '{filename}': {pinecone_msg}")
    except Exception as e:
        pinecone_msg = f"Error during Pinecone deletion: {e}"
        print(pinecone_msg)

    try:
        mongo_deleted = delete_file_record_from_mongo(filename)
        if mongo_deleted:
            mongo_msg = f"File '{filename}' deleted from MongoDB."
        else:
            mongo_msg = f"File '{filename}' not found in MongoDB or not deleted."
    except HTTPException as e:
        mongo_msg = f"Error during MongoDB deletion: {e.detail}"
        print(mongo_msg)
        raise e
    except Exception as e:
        mongo_msg = f"Error during MongoDB deletion: {e}"
        print(mongo_msg)
        
    return DeleteResult(
        filename=filename,
        deleted_mongo=mongo_deleted,
        deleted_pinecone=pinecone_deleted,
        mongo_message=mongo_msg,
        pinecone_message=pinecone_msg
    )

@app.get("/pinecone-info/", response_model=Dict[str, Any])
async def get_pinecone_info_endpoint():
    """
    Retrieves and returns information about the configured Pinecone index.
    """
    try:
        info = get_pinecone_index_info()
        return info
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve Pinecone info: {e}")

# --- NEW API ENDPOINT: Delete entire Pinecone index (for development) ---
@app.delete("/pinecone-index/", response_model=PineconeIndexDeleteResponse)
async def delete_pinecone_index_endpoint(
    confirm: bool = Query(
        False, 
        description="Set to `true` to confirm deletion of the entire Pinecone index. USE WITH EXTREME CAUTION!"
    )
):
    """
    Deletes the entire Pinecone index. This operation is irreversible.
    Requires `confirm=true` as a query parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required to delete the entire Pinecone index. "
                   "Add `?confirm=true` to the request URL."
        )
    
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not index_name:
        raise HTTPException(status_code=500, detail="PINECONE_INDEX_NAME environment variable not set.")

    try:
        delete_result = delete_pinecone_index(index_name)
        return PineconeIndexDeleteResponse(
            index_name=delete_result["index_name"],
            deleted=delete_result["deleted"],
            message=delete_result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Pinecone index: {e}")

@app.post("/chat")
async def chat(request: Request):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)