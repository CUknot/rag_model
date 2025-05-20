from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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

# --- API Endpoints ---
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
