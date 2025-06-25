import os
import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

# Load API keys and index name
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validation
if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
    raise ValueError("Missing Pinecone API key or index name in environment variables.")

if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key in environment variables.")

# Initialize Pinecone and OpenAI clients
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
client = OpenAI(api_key=OPENAI_API_KEY)

# Load SentenceTransformer model
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

    # Combine all columns into one text string per row
    texts = df.astype(str).agg(" ".join, axis=1).tolist()
    embeddings = model.encode(texts).tolist()

    # Prepare vectors for Pinecone
    vectors = [(f"id-{i}", embeddings[i], {"text": texts[i]}) for i in range(len(texts))]
    index.upsert(vectors=vectors)
    return f"Upserted {len(vectors)} vectors into index '{PINECONE_INDEX_NAME}'"


def query_index(query_text, top_k=5):
    query_vector = model.encode([query_text])[0].tolist()
    response = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    matches = response.get("matches", [])
    if not matches:
        return "No relevant matches found."

    top_match_text = matches[0]["metadata"].get("text", "")

    # Use OpenAI to extract structured details
    structured_output = extract_with_openai(top_match_text)
    return structured_output


def extract_with_openai(text):
    system_prompt = (
        "Extract structured electrical component details from the following text in the format: "
        "<component> = <quantity>. Include mounting height and dimensions if mentioned."
    )

    response = client.chat.completions.create(
        model="gpt-4o",  # You may change this to "gpt-3.5-turbo" if needed
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()
