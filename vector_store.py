import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import pandas as pd

load_dotenv()

# Load Pinecone credentials and setup
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
PINECONE_ENV = os.getenv("PINECONE_ENV", "gcp-starter")  # default if missing

if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
    raise ValueError("Missing Pinecone API key or Index name in environment variables.")

pc = Pinecone(api_key=PINECONE_API_KEY)

# Check or create index
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    print(f"Creating index '{PINECONE_INDEX_NAME}'...")
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=768,  # Model dimension for all-MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")  # Update if needed
    )

index = pc.Index(PINECONE_INDEX_NAME)

# Load the embedding model
model = SentenceTransformer('all-mpnet-base-v2')

def read_file(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".csv":
        df = pd.read_csv(file_path)
    elif ext in [".xls", ".xlsx"]:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    return df

def embed_and_store(file_path):
    df = read_file(file_path)

    # Combine all columns into a single string per row
    texts = df.astype(str).agg(" ".join, axis=1).tolist()
    embeddings = model.encode(texts).tolist()

    vectors = []
    for i, (embedding, text) in enumerate(zip(embeddings, texts)):
        vectors.append({
            "id": f"id-{i}",
            "values": embedding,
            "metadata": {"text": text}  # storing for easier query viewing
        })

    index.upsert(vectors=vectors)
    return f"Upserted {len(vectors)} vectors."




def query_index(query_text, top_k=1):
    query_vector = model.encode([query_text])[0].tolist()
    response = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    if response and response.get("matches"):
        top_match = response["matches"][0]
        text = top_match.get("metadata", {}).get("text", "No metadata")
        score = round(top_match.get("score", 0), 3)
        return f"{text} — (score {score})"
    else:
        return "No results found."
