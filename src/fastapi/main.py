from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Content, Part
from datetime import datetime # Import datetime

# Import the Pinecone functions
from src.pinecone.main import (
    upload_text_to_pinecone,
    get_pinecone_index_info,
    delete_file_from_pinecone,
    delete_pinecone_index,
    _get_pinecone_index,
    _get_pinecone_client
)

# Import the Model functions
from src.model.main import get_response_from_llm # Still commented out as in your provided code

load_dotenv()

app = FastAPI()

# --- Configuration ---
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME")
MONGODB_COLLECTION_FILES = "files"
MONGODB_COLLECTION_CHAT_LOGS = os.getenv("MONGODB_COLLECTION_CHAT_LOGS") 

# --- Initialize MongoDB ---
mongo_client: Optional[MongoClient] = None
files_collection = None
chat_logs_collection = None # New collection variable
try:
    mongo_client = MongoClient(MONGODB_URI)
    mongodb = mongo_client[MONGODB_DATABASE_NAME]
    files_collection = mongodb[MONGODB_COLLECTION_FILES]
    chat_logs_collection = mongodb[MONGODB_COLLECTION_CHAT_LOGS]
    print("MongoDB initialized successfully.")
except Exception as e:
    print(f"Error initializing MongoDB: {e}")

# --- Data Models ---
class UploadFileRequest(BaseModel):
    title: str
    content: str
    category: str

class UploadFileResponse(BaseModel):
    title: str
    num_chunks: int
    pinecone_status: str
    mongo_status: str

class FileRecord(BaseModel):
    title: str
    content: str
    category: str
    date: str # Date is part of the record, even if auto-generated
    num_chunks: Optional[int] = 0

class DeleteResult(BaseModel):
    title: str
    deleted_mongo: bool
    deleted_pinecone: bool
    mongo_message: Optional[str] = None
    pinecone_message: Optional[str] = None

class PineconeIndexDeleteResponse(BaseModel):
    index_name: str
    deleted: bool
    message: str

class Request(BaseModel):
    prompt: List[Content]

index_name = os.getenv("PINECONE_INDEX_NAME")
namespace = os.getenv("PINECONE_NAMESPACE")
index = _get_pinecone_index(index_name)
def get_context(user_input: str):
    keywords = ['rag','RAG']
    print("get")
    for word in keywords:
            if word in user_input.lower():
                results = index.search(
                namespace=namespace,
                query={
                    "top_k": 10,
                    "inputs": {
                        "text": user_input
                    }
                }
                )
                print(f"Results: {results}")
                return results['result']['hits'][0]['fields']['chunk_text']    
    return None

# --- Helper Functions (MongoDB Operations) ---
def get_all_file_records() -> List[FileRecord]:
    """
    Retrieves all file records (title, content, category, date, num_chunks) from the MongoDB collection.
    """
    if files_collection is not None:
        records = []
        for document in files_collection.find():
            # Safely get values, providing defaults for potentially missing fields
            doc_title = document.get("title") # No longer trying 'filename' as a primary title
            doc_content = document.get("content")
            doc_category = document.get("category", "general")
            doc_date = document.get("date", datetime.now().strftime("%Y-%m-%d"))
            doc_num_chunks = document.get("num_chunks", 0)

            # Ensure title and content are present before creating FileRecord
            if doc_title is not None and doc_content is not None:
                records.append(FileRecord(
                    title=doc_title,
                    content=doc_content,
                    category=doc_category,
                    date=doc_date,
                    num_chunks=doc_num_chunks
                ))
            else:
                # Log or handle documents that don't conform to the expected structure
                print(f"Skipping document due to missing title or content: {document}")
        return records
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def get_file_record_from_mongo(title: str) -> Optional[FileRecord]:
    """
    Retrieves a single file record by title from MongoDB.
    """
    if files_collection is not None:
        document = files_collection.find_one({"title": title}) # Only search by 'title' now
        if document:
            return FileRecord(
                title=document.get("title"),
                content=document.get("content"),
                category=document.get("category", "general"),
                date=document.get("date", datetime.now().strftime("%Y-%m-%d")),
                num_chunks=document.get("num_chunks", 0)
            )
        return None
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def add_file_record(title: str, content: str, category: str, date: str, num_chunks: int) -> bool:
    """
    Adds a new file record (title, content, category, date, num_chunks) to the MongoDB collection.
    """
    if files_collection is not None:
        file_data = {
            "title": title,
            "content": content,
            "category": category,
            "date": date,
            "num_chunks": num_chunks
        }
        try:
            if files_collection.find_one({"title": title}):
                raise HTTPException(status_code=409, detail=f"Note with title '{title}' already exists in MongoDB.")

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

def delete_file_record_from_mongo(title: str) -> bool:
    """
    Deletes a file record from the MongoDB collection by title.
    """
    if files_collection is not None:
        try:
            deleted_result = files_collection.delete_one({"title": title})
            return deleted_result.deleted_count > 0
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete note from MongoDB: {e}",
            )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def update_file_record_in_mongo(original_title: str, new_title: str, new_content: str, new_category: str, new_date: str) -> bool:
    """
    Updates an existing file record in the MongoDB collection.
    """
    if files_collection is not None:
        try:
            update_result = files_collection.update_one(
                {"title": original_title},
                {"$set": {
                    "title": new_title,
                    "content": new_content,
                    "category": new_category,
                    "date": new_date
                }}
            )
            return update_result.modified_count > 0
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update note in MongoDB: {e}",
            )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to access MongoDB. Check the server logs for connection errors.",
        )

def add_chat_log_entry(user_prompt: str, llm_response: str) -> bool:
    """
    Adds a new chat log entry to the MongoDB collection.
    """
    if chat_logs_collection is not None:
        log_data = {
            "user_prompt": user_prompt,
            "llm_response": llm_response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            chat_logs_collection.insert_one(log_data)
            return True
        except Exception as e:
            print(f"Error adding chat log to MongoDB: {e}")
            return False
    else:
        print("Chat logs collection not initialized.")
        return False

# --- API Endpoints ---
@app.get("/files/", response_model=List[FileRecord])
async def get_files():
    """
    Returns a list of all filenames (titles), content, categories, and dates in the database.
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
    and records the note (title, content, category, date, chunk count) in MongoDB.
    The 'date' will be automatically set to today's date.
    """
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    if not request.category.strip():
        raise HTTPException(status_code=400, detail="Category cannot be empty.")

    # Automatically set the date to today
    current_date = datetime.now().strftime("%Y-%m-%d")

    pinecone_upload_successful = False
    num_chunks_uploaded = 0
    pinecone_message = "Pending"

    try:
        # Pass the title (filename) and content for Pinecone upload
        num_chunks_uploaded = upload_text_to_pinecone(
            filename=request.title, # Pinecone uses filename, so use title here
            text=request.content,
            category=request.category
        )
        pinecone_upload_successful = True
        pinecone_message = "Success"
    except Exception as e:
        pinecone_message = f"Pinecone upload failed: {e}"
        print(f"Error during Pinecone upload for '{request.title}': {e}")
        raise HTTPException(status_code=500, detail=pinecone_message)

    mongo_record_successful = False
    mongo_message = "Pending"

    try:
        # Use the automatically generated date
        if add_file_record(request.title, request.content, request.category, current_date, num_chunks_uploaded):
            mongo_record_successful = True
            mongo_message = "Success"
        else:
            mongo_message = "Failed to add record to MongoDB after Pinecone upload."
    except HTTPException as e:
        mongo_message = f"MongoDB record failed: {e.detail}"
        print(f"Error during MongoDB record for '{request.title}': {e.detail}")
        raise e
    except Exception as e:
        mongo_message = f"MongoDB record failed: {e}"
        print(f"Error during MongoDB record for '{request.title}': {e}")
        raise HTTPException(status_code=500, detail=mongo_message)

    return UploadFileResponse(
        title=request.title,
        num_chunks=num_chunks_uploaded,
        pinecone_status=pinecone_message,
        mongo_status=mongo_message
    )

@app.delete("/files/", response_model=DeleteResult)
async def delete_file_and_vectors(title: str = Query(..., description="The title of the note to delete.")):
    """
    Deletes a note record from MongoDB and its associated vectors from Pinecone.
    The num_chunks and category are fetched from MongoDB.
    """
    mongo_deleted = False
    pinecone_deleted = False
    mongo_msg = "Pending"
    pinecone_msg = "Pending"

    # Fetch the file record first to get num_chunks and category for Pinecone
    file_record = get_file_record_from_mongo(title)

    if not file_record:
        raise HTTPException(status_code=404, detail=f"Note '{title}' not found in MongoDB.")

    # Use the retrieved num_chunks and category for Pinecone deletion
    num_chunks = file_record.num_chunks
    category = file_record.category

    try:
        # Pinecone deletion
        pinecone_delete_result = delete_file_from_pinecone(title, num_chunks, category)
        pinecone_deleted = pinecone_delete_result.get("deleted", False)
        pinecone_msg = pinecone_delete_result.get("message", "Unknown Pinecone deletion status.")
        if not pinecone_deleted:
            print(f"Warning: Pinecone deletion failed for '{title}': {pinecone_msg}")
    except Exception as e:
        pinecone_msg = f"Error during Pinecone deletion: {e}"
        print(pinecone_msg)

    try:
        # MongoDB deletion
        mongo_deleted = delete_file_record_from_mongo(title)
        if mongo_deleted:
            mongo_msg = f"Note '{title}' deleted from MongoDB."
        else:
            mongo_msg = f"Note '{title}' not found in MongoDB or not deleted."
    except HTTPException as e:
        mongo_msg = f"Error during MongoDB deletion: {e.detail}"
        print(mongo_msg)
        raise e
    except Exception as e:
        mongo_msg = f"Error during MongoDB deletion: {e}"
        print(mongo_msg)

    return DeleteResult(
        title=title,
        deleted_mongo=mongo_deleted,
        deleted_pinecone=pinecone_deleted,
        mongo_message=mongo_msg,
        pinecone_message=pinecone_msg
    )

@app.put("/files/{original_title}", response_model=FileRecord)
async def update_file(original_title: str, updated_record: UploadFileRequest):
    """
    Updates an existing note record in MongoDB and potentially Pinecone if content changes.
    The 'date' field will be updated to today's date upon modification.
    """
    # First, get the existing record to compare and get Pinecone-related info
    existing_record = get_file_record_from_mongo(original_title)
    if not existing_record:
        raise HTTPException(status_code=404, detail=f"Note '{original_title}' not found in MongoDB.")

    mongo_updated = False
    pinecone_reuploaded = False

    # Get today's date for the update
    updated_date = datetime.now().strftime("%Y-%m-%d")

    # Check if content, category, or title has changed, if so, re-upload to Pinecone
    # Note: If only title changes, old vectors are orphaned and new ones created under new title
    # This logic assumes Pinecone uses the filename (title) as the key/namespace.
    if (existing_record.content != updated_record.content or
        existing_record.category != updated_record.category or
        existing_record.title != updated_record.title):
        try:
            # Delete old vectors from Pinecone using the original title and category
            delete_file_from_pinecone(existing_record.title, existing_record.num_chunks, existing_record.category)

            # Upload new content to Pinecone with the potentially new title/category
            num_chunks_uploaded = upload_text_to_pinecone(
                filename=updated_record.title, # Use the potentially new title for Pinecone
                text=updated_record.content,
                category=updated_record.category
            )
            pinecone_reuploaded = True
            # Note: num_chunks is not directly part of UploadFileRequest anymore
            # But the add_file_record (if a new record is somehow made) and
            # get_file_record_from_mongo will handle it.
            # For update, we don't necessarily need to pass it back to updated_record here
            # as it's not a field expected by the Pydantic model for input.
        except Exception as e:
            print(f"Warning: Pinecone re-upload failed for '{updated_record.title}': {e}")
            # Decide if you want to abort the MongoDB update or proceed.

    try:
        mongo_updated = update_file_record_in_mongo(
            original_title,
            updated_record.title,
            updated_record.content,
            updated_record.category,
            updated_date # Use today's date for the update
        )
        if not mongo_updated:
            raise HTTPException(status_code=400, detail="No changes detected or update failed in MongoDB.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update note in MongoDB: {e}")

    # Fetch the updated record to return
    updated_note = get_file_record_from_mongo(updated_record.title)
    if not updated_note:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated note from MongoDB.")
    return updated_note

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

@app.delete("/pinecone-index/", response_model=PineconeIndexDeleteResponse)
async def delete_pinecone_index_endpoint(
    confirm: bool = Query(
        True,
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
async def post_chat(request: Request):
    context = None
    # 1.รับ context จาก PC ถ้าจะเป็นต้องใช้
    user_input = request.prompt[-1].parts[0].text
    if get_context(user_input):
        context = get_context(user_input)
    print(f"Context: {context}")

    # 2.ส่งคำถามไปหาแชท
    result = get_response_from_llm(request.prompt, context)
    
    # Extract the LLM's response text safely
    llm_response_text = result.text if hasattr(result, 'text') else str(result)
    
    request.prompt.append(Content(role="assistant", parts=[Part(text=llm_response_text)]))

    # Log the chat interaction to MongoDB
    if not add_chat_log_entry(user_input, request.prompt[-1].parts[0].text):
        print("Failed to save chat log entry to MongoDB.")
    return request

@app.get("/get_context/")
async def get_context_endpoint(query: str = Query(..., description="The user query to retrieve context for.")):
    """
    Retrieves and returns relevant context from Pinecone based on the provided query.
    This endpoint is useful for debugging the RAG context retrieval mechanism.
    """
    try:
        context = get_context(query)
        if context is not None:
            return {"query": query, "context": context, "status": "Context found"}
        else:
            return {"query": query, "context": None, "status": "No relevant context found in Pinecone for the given query."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving context: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)