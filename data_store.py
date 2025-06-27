

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
