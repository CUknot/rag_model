import os
import random
import itertools
from pinecone.grpc import PineconeGRPC as Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
pinecone_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")

# Initialize Pinecone GRPC client
pc = Pinecone(api_key=pinecone_key)

# Create index if it doesn't exist
if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "llama-text-embed-v2",
            "field_map": {"text": "chunk_text"}
        }
    )

# Get index host and connect
index_description = pc.describe_index(index_name)
index = pc.Index(host=index_description.host)

# Sample long text input
text = """
This is a long piece of text that we want to split into smaller chunks using RecursiveCharacterTextSplitter. 
Each chunk will be processed and then uploaded to Pinecone along with an embedding. 
We're simulating this with dummy embeddings for now. In a real scenario, you would generate embeddings 
using a model like OpenAI, HuggingFace Transformers, etc.
"""

# Step 1: Split text into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=40,
    add_start_index=True
)
chunks = text_splitter.create_documents([text])

# Step 2: Prepare vectors (with dummy embeddings)
vector_dim = 128  # You can change this if needed
vectors = []
for i, chunk in enumerate(chunks):
    vector_id = f"text_chunk{i}_{chunk.metadata['start_index']}"
    values = [random.random() for _ in range(vector_dim)]  # Dummy 128-dim float vector
    metadata = {
        "filename": "example.txt",
        "category": "example",
        "chunk": chunk.page_content
    }
    vectors.append((vector_id, values, metadata))

# Step 3: Chunking helper
def chunks_iter(iterable, batch_size=100):
    """Yield successive batch_size-sized chunks from iterable."""
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))

# Step 4: Upsert in batches
for batch in chunks_iter(vectors, batch_size=100):
    index.upsert(vectors=batch)

print("✅ Upsert completed successfully.")