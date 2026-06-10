# build_index.py
import os
import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Load the JSON file
with open("processed_law.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def extract_chunks(data):
    act_title = data.get("act_title", "")
    chunks = []

    for i, sec in enumerate(data.get("sections", [])):
        text = sec.get("section_content", "").strip()
        if text:
            chunks.append({
                "act_title": act_title,
                "chunk_type": "section",
                "chunk_id": f"{act_title}-sec-{i+1}",
                "content": text
            })

    for i, foot in enumerate(data.get("footnotes", [])):
        text = foot.get("footnote_text", "").strip()
        if text:
            chunks.append({
                "act_title": act_title,
                "chunk_type": "footnote",
                "chunk_id": f"{act_title}-footnote-{i+1}",
                "content": text
            })

    return chunks

# Combine all chunks
all_chunks = []
for act in data["acts"]:
    all_chunks.extend(extract_chunks(act))

# Embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")
texts = [chunk['content'] for chunk in all_chunks]
metadata = all_chunks

embeddings = model.encode(texts, show_progress_bar=True).astype("float32")

# FAISS
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

# Save
os.makedirs("embeddings", exist_ok=True)
faiss.write_index(index, "embeddings/faiss.index")
with open("embeddings/chunk_metadata.pkl", "wb") as f:
    pickle.dump(metadata, f)

print("✅ Rebuilt FAISS index and saved.")
