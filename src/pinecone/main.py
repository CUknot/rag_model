import os
from pinecone import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional

def _get_pinecone_client():
    """Helper to initialize and return the Pinecone client."""
    pinecone_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_key:
        raise ValueError("PINECONE_API_KEY environment variable not set.")
    return Pinecone(api_key=pinecone_key)

def _get_pinecone_index(index_name: str) -> Pinecone.Index:
    """Helper to get a Pinecone index instance."""
    pc = _get_pinecone_client()
    if not pc.has_index(index_name):
        raise ValueError(f"Pinecone index '{index_name}' does not exist.")
    index_description = pc.describe_index(index_name)
    return pc.Index(host=index_description.host)

def get_pinecone_index_info() -> Dict[str, Any]:
    """
    Retrieves and returns information about the Pinecone index,
    including detailed statistics about namespaces and vector counts.

    Returns:
        Dict[str, Any]: A dictionary containing index description and statistics.
    """
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not pinecone_key or not index_name:
        raise ValueError("PINECONE_API_KEY or PINECONE_INDEX_NAME environment variables not set.")

    pc = _get_pinecone_client()

    if not pc.has_index(index_name):
        return {"status": "Index not found", "index_name": index_name}
    
    index = _get_pinecone_index(index_name) # Get the index object
    index_description = pc.describe_index(index_name)
    
    # Get index statistics, which includes namespace details
    index_stats = index.describe_index_stats() 

    return {
        "index_name": index_name,
        "description": index_description.to_dict(), # Convert Description object to dict
        "statistics": index_stats.to_dict() # Convert IndexStats object to dict
    }

def upload_text_to_pinecone(filename: str, text: str, category: str = "None") -> int:
    """
    Splits a long text into chunks, prepares records, and uploads them to Pinecone
    using upsert_records, relying on Pinecone's server-side embedding.

    Args:
        filename (str): The name of the file being uploaded (used for record IDs and metadata).
        text (str): The long text document to be processed and uploaded.
        category (str, optional): The category of the document, used as metadata. Defaults to "None".
    Returns:
        int: The number of chunks successfully processed and prepared for upsert.
    """
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    # Use the category as the namespace, fallback to default if not provided
    namespace = os.getenv("PINECONE_NAMESPACE", "") 
    if not namespace:
        namespace = "default" 

    pc = _get_pinecone_client()

    actual_model_dimension = 1024 # **CRITICAL: Set this to the actual dimension of llama-text-embed-v2**

    if not pc.has_index(index_name):
        print(f"Creating Pinecone index '{index_name}' with dimension {actual_model_dimension}...")
        pc.create_index_for_model(
            name=index_name,
            cloud="aws",
            region="us-east-1", 
            embed={
                "model": "llama-text-embed-v2",
                "field_map": {"text": "chunk_text"}
            },
        )
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")
        index_description = pc.describe_index(index_name)
        if index_description.dimension != actual_model_dimension:
            print(f"WARNING: Existing index dimension ({index_description.dimension}) does not match "
                  f"the expected model dimension ({actual_model_dimension}). This could cause "
                  "issues if the index's embedding config is different or changed.")

    index = _get_pinecone_index(index_name)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=50,
        add_start_index=True
    )
    chunks = text_splitter.create_documents([text])
    print(f"Split text into {len(chunks)} chunks.")

    records_to_upsert = []
    for i, chunk in enumerate(chunks):
        record_id = f"{filename}_{i}"
        record = {
            "_id": record_id,
            "chunk_text": chunk.page_content, 
            "category": category,
            "filename": filename, 
            "chunk_index": i, 
            "start_index": chunk.metadata['start_index'], 
        }
        records_to_upsert.append(record)
    print(f"Prepared {len(records_to_upsert)} records for upsertion.")

    print(f"Upserting records into namespace '{namespace}'...")

    batch_size = 100
    batch_count = 0
    for i in range(0, len(records_to_upsert), batch_size):
        batch = records_to_upsert[i:i + batch_size]
        index.upsert_records(namespace, batch) 
        batch_count += 1
    
    print(f"✅ Upsert completed successfully. {batch_count} batches uploaded to namespace '{namespace}'")
    return len(records_to_upsert)

def delete_file_from_pinecone(filename: str, num_chunks: int, category: str = "None") -> Dict[str, Any]:
    """
    Deletes all vectors (chunks) associated with a specific filename from Pinecone.
    """
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    namespace = category if category != "None" else os.getenv("PINECONE_NAMESPACE", "")
    if not namespace:
        namespace = "default"

    pc = _get_pinecone_client()
    
    if not pc.has_index(index_name):
        return {"filename": filename, "deleted": False, "message": f"Index '{index_name}' not found."}

    index = _get_pinecone_index(index_name)

    ids_to_delete = [f"{filename}_{i}" for i in range(num_chunks)]
    print(f"Attempting to delete {len(ids_to_delete)} vectors for file '{filename}' from namespace '{namespace}'.")

    try:
        response = index.delete(ids=ids_to_delete, namespace=namespace)
        
        return {
            "filename": filename,
            "deleted": True,
            "count_attempted": len(ids_to_delete),
            "namespace": namespace,
            "message": "Deletion request sent to Pinecone. Verify count if critical."
        }
    except Exception as e:
        return {
            "filename": filename,
            "deleted": False,
            "message": f"Error deleting from Pinecone: {e}",
            "namespace": namespace
        }
    
# --- DEV: Delete entire Pinecone index ---
def delete_pinecone_index(index_name: str) -> Dict[str, Any]:
    """
    Deletes the entire Pinecone index. USE WITH EXTREME CAUTION.

    Args:
        index_name (str): The name of the index to delete.

    Returns:
        Dict[str, Any]: A dictionary indicating the outcome of the deletion.
    """
    pc = _get_pinecone_client()

    if not pc.has_index(index_name):
        return {"index_name": index_name, "deleted": False, "message": f"Index '{index_name}' does not exist."}
    
    try:
        print(f"Attempting to delete Pinecone index: '{index_name}'...")
        pc.delete_index(index_name)
        print(f"✅ Pinecone index '{index_name}' deleted successfully.")
        return {"index_name": index_name, "deleted": True, "message": f"Index '{index_name}' deleted successfully."}
    except Exception as e:
        print(f"Error deleting Pinecone index '{index_name}': {e}")
        return {"index_name": index_name, "deleted": False, "message": f"Error deleting index: {e}"}