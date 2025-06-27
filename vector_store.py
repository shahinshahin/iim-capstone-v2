import os
import json
import logging
import pandas as pd
import datetime
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from openai import OpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
    raise ValueError("Missing Pinecone API key or index name.")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key.")

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

model = SentenceTransformer('all-mpnet-base-v2')
EMBED_DIM = 768

def recreate_index():
    existing_indexes = pc.list_indexes().names()
    if PINECONE_INDEX_NAME in existing_indexes:
        logging.info(f"Deleting existing index: {PINECONE_INDEX_NAME}")
        pc.delete_index(PINECONE_INDEX_NAME)

    logging.info(f"Creating new index: {PINECONE_INDEX_NAME}")
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

    while True:
        status = pc.describe_index(PINECONE_INDEX_NAME).status
        if status.get("ready"):
            break

def read_file(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext in [".xls", ".xlsx"]:
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def extract_structured_info(description_text: str):
    if not description_text.strip():
        return []

    system_prompt = (
        "Extract all raw materials and their quantities from the electrical BOQ description below.\n"
        "Return a JSON array like: [{\"Raw Materials\": \"<name>\", \"Sub QTY\": <qty>}]\n"
        "If no quantity is mentioned, assume 1.\n"
        "Avoid explanation — return only JSON.\n\n"
        "Description:\n"
    )

    full_prompt = system_prompt + description_text.strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        json_start = content.find('[')
        json_end = content.rfind(']') + 1
        raw_json = content[json_start:json_end]
        return json.loads(raw_json)

    except Exception as e:
        logger.warning(f"GPT failed for text: '{description_text}'. Error: {e}")
        return [{"Raw Materials": description_text.strip(), "Sub QTY": 1}]
def embed_and_store(file_path):
    recreate_index()
    index = pc.Index(PINECONE_INDEX_NAME)
    df = read_file(file_path)

    if 'Description' not in df.columns:
        raise ValueError("Input file must contain a 'Description' column.")

    texts = df['Description'].astype(str).tolist()
    embeddings = model.encode(texts).tolist()

    vectors = []
    vector_ids = []

    for i, text in enumerate(texts):
        extracted_items = extract_structured_info(text)
        if not extracted_items:
            metadata = {"text": text, "Raw Materials": "", "Sub QTY": ""}
            vector_id = f"id-{i}"
            vectors.append((vector_id, embeddings[i], metadata))
            vector_ids.append(vector_id)
        else:
            for j, item in enumerate(extracted_items):
                metadata = {"Raw Materials": item.get("Raw Materials", ""), "Sub QTY": item.get("Sub QTY", 0),"Original": text}  # Ensure consistent field}
                vector_id = f"id-{i}-{j}"
                vectors.append((vector_id, embeddings[i], metadata))
                vector_ids.append(vector_id)

    index.upsert(vectors=vectors)
    logger.info(f"Upserted {len(vectors)} vectors into index '{PINECONE_INDEX_NAME}'")

    # ✅ Save vector IDs locally (e.g., JSON file)
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/vector_ids.json", "w") as f:
        json.dump(vector_ids, f)

    return f"Upserted {len(vectors)} vectors"


def query_index(query_text, top_k=5):
    index = pc.Index(PINECONE_INDEX_NAME)
    query_vector = model.encode([query_text])[0].tolist()
    response = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    matches = response.get("matches", [])
    if not matches:
        return []

    results = []
    for match in matches:
        metadata = match.get("metadata", {})
        results.append({
            "Raw Materials": metadata.get("Raw Materials", ""),
            "Sub QTY": metadata.get("Sub QTY", 1),
            "Original": metadata.get("text", "")
        })

    return results

def compute_material_cost(materials: list, material_file_path="material_details/material_details.xlsx"):
    if not os.path.exists(material_file_path):
        logger.error("Material price file not found at %s", material_file_path)
        return []

    try:
        df = pd.read_excel(material_file_path)
        df.fillna(0, inplace=True)

        if "Raw Material" not in df.columns or "Unit Price" not in df.columns:
            logger.error("Missing required columns in material file")
            return []

        if "Discount" not in df.columns:
            df["Discount"] = 0

        cost_summary = []
        grand_total = 0

        for mat in materials:
            raw_material = str(mat.get("Raw Materials", "")).strip()
            raw_qty = mat.get("Sub QTY", 0)

            # Safe parsing of quantity
            try:
                qty = float(raw_qty) if str(raw_qty).strip() else 0
            except ValueError:
                logger.warning(f"Invalid quantity '{raw_qty}' for material '{raw_material}', defaulting to 0.")
                qty = 0

            # Exact match only
            match = df[df["Raw Material"].str.lower().str.strip() == raw_material.lower()]

            if not match.empty:
                price = float(match.iloc[0]["Unit Price"])
                discount = float(match.iloc[0]["Discount"])
                matched_material = match.iloc[0]["Raw Material"]
            else:
                logger.warning(f"No price match found for: '{raw_material}'")
                price = 0
                discount = 0
                matched_material = raw_material  # fallback

            total = qty * price * ((100 - discount) / 100)
            grand_total += total

            cost_summary.append({
                "Raw Material": matched_material,
                "Quantity": qty,
                "Unit Price": price,
                "Discount": discount,
                "Total": round(total, 2)
            })

        # Add Grand Total row
        cost_summary.append({
            "Raw Material": "GRAND TOTAL",
            "Quantity": "",
            "Unit Price": "",
            "Discount": "",
            "Total": round(grand_total, 2)
        })

        # Save to timestamped Excel file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"outputs/material_cost_summary_{timestamp}.xlsx"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pd.DataFrame(cost_summary).to_excel(output_path, index=False)
        logger.info("Material cost summary saved to %s", output_path)

        return cost_summary

    except Exception as e:
        logger.exception("Error computing material cost: %s", str(e))
        return []


def save_material_metadata_to_excel(metadata_list, file_path):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        rows = []
        for metadata in metadata_list:
            raw = metadata.get("Raw Materials", "")
            qty = metadata.get("Sub QTY", "")
            rows.append({"Raw Material": raw, "Sub QTY": qty})

        df = pd.DataFrame(rows)
        df.to_excel(file_path, index=False)
        logger.info("Saved raw material metadata to Excel at %s", file_path)

    except PermissionError as e:
        logger.error(f"Permission denied: close the file if open. Path: {file_path}")
    except Exception as e:
        logger.exception("Failed to save raw material metadata: %s", str(e))


def embed_and_store(file_path):
    recreate_index()
    index = pc.Index(PINECONE_INDEX_NAME)
    df = read_file(file_path)

    if 'Description' not in df.columns:
        raise ValueError("Input file must contain a 'Description' column.")

    texts = df['Description'].astype(str).tolist()
    embeddings = model.encode(texts).tolist()

    vectors = []
    all_metadata = []

    for i, text in enumerate(texts):
        extracted_items = extract_structured_info(text)
        if not extracted_items:
            metadata = {"text": text, "Raw Materials": "", "Sub QTY": ""}
            vectors.append((f"id-{i}", embeddings[i], metadata))
            all_metadata.append(metadata)
        else:
            for j, item in enumerate(extracted_items):
                metadata = {
                    "text": text,
                    "Raw Materials": item.get("Raw Materials", ""),
                    "Sub QTY": item.get("Sub QTY", 0)
                }
                vectors.append((f"id-{i}-{j}", embeddings[i], metadata))
                all_metadata.append(metadata)

    index.upsert(vectors=vectors)
    logger.info(f"Upserted {len(vectors)} vectors into index '{PINECONE_INDEX_NAME}'")

    # ✅ Save metadata to file
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/pinecone_metadata.json", "w") as f:
        json.dump(all_metadata, f, indent=2)

    return f"Upserted {len(vectors)} vectors"
def get_all_pinecone_data():
    try:
        with open("outputs/pinecone_metadata.json", "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.warning("No local Pinecone metadata found or failed to load.")
        return []
