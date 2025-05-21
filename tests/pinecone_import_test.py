import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter

def upload_text_to_pinecone(filename: str, text: str, category: str = "None"):
    """
    Splits a long text into chunks, prepares records, and uploads them to Pinecone
    using upsert_records, relying on Pinecone's server-side embedding.

    Args:
        text (str): The long text document to be processed and uploaded.
        namespace (str, optional): The namespace to upsert the data into. Defaults to None.
    """
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    namespace = os.getenv("PINECONE_NAMESPACE")

    pc = Pinecone(api_key=pinecone_key)

    actual_model_dimension = 1024 # **CRITICAL: Set this to the actual dimension of llama-text-embed-v2**

    if not pc.has_index(index_name):
        print(f"Creating Pinecone index '{index_name}' with dimension {actual_model_dimension}...")
        pc.create_index_for_model(
            name=index_name,
            cloud="aws",
            region="us-east-1", 
            embed={
                "model": "llama-text-embed-v2",
                "field_map": {"text": "chunk_text"} # This tells Pinecone to embed the 'chunk_text' field
            },
            dimension=actual_model_dimension # Ensure this matches the model's output dimension
        )
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")
        # Optional: Verify existing index dimension matches expected for the model
        index_description = pc.describe_index(index_name)
        if index_description.dimension != actual_model_dimension:
            print(f"WARNING: Existing index dimension ({index_description.dimension}) does not match "
                  f"the expected model dimension ({actual_model_dimension}). This could cause "
                  "issues if the index's embedding config is different or changed.")

    # Get index host and connect
    index_description = pc.describe_index(index_name)
    index = pc.Index(host=index_description.host)

    # Step 1: Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=50,
        add_start_index=True
    )
    chunks = text_splitter.create_documents([text])
    print(f"Split text into {len(chunks)} chunks.")

    # Step 2: Prepare records for upsert_records
    # Each record needs an _id, and the text to be embedded (named 'chunk_text' per field_map)
    # Plus any other metadata you want to store.
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

    # Step 3: Upsert in batches using upsert_records
    print(f"Upserting records into namespace '{namespace if namespace else 'default'}'...")

    batch_size = 100 # Adjust batch size as needed
    batch_count = 0
    for i in range(0, len(records_to_upsert), batch_size):
        batch = records_to_upsert[i:i + batch_size]
        index.upsert_records(namespace, batch)
        batch_count += 1
    
    print(f"✅ Upsert completed successfully. {batch_count} batches uploaded to namespace '{namespace if namespace else 'default'}'")


def main():
    """
    Loads environment variables, defines sample text, and calls the
    upload_text_to_pinecone function to demonstrate its usage.
    """
    load_dotenv()
    print("Environment variables loaded (if .env file exists).")

    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")

    if not pinecone_api_key or not pinecone_index_name:
        print("ERROR: PINECONE_API_KEY or PINECONE_INDEX_NAME environment variables are not set.")
        print("Please set them in your environment or in a .env file.")
        print("Exiting without running Pinecone upload.")
        return

    sample_long_text = """
    This is a demonstration text for running the Pinecone upload function.
    It simulates a real-world scenario where you have a substantial piece of content
    that you want to index in Pinecone for vector search. The `upload_text_to_pinecone`
    function handles the text splitting, and batch upserting.
    This script serves as a simple way to verify the end-to-end flow of the function
    without needing to write a full unit test with mocks for every run.
    It's useful for quick checks or as part of a larger integration testing suite.
    Here is some more text to ensure we get multiple chunks. We can talk about different topics
    like the weather, technology, or current events. For example, today's weather is sunny,
    and the latest in AI is truly fascinating with models like GPT-4o. Remember to always
    stay hydrated!
    """

    print("\n--- Starting Pinecone Upload Demonstration for Sample Text ---")
    upload_text_to_pinecone(
        filename="sample_text.txt",
        text=sample_long_text,
        category="demonstration"  
    )
    print("\n--- Pinecone Upload Demonstration Finished ---")

if __name__ == "__main__":
    main()