import json
import faiss
import numpy as np
from langchain_ollama import OllamaEmbeddings

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
PDF_CHUNKS_FILE = "dataset.json"
YT_CHUNKS_FILE = "cnas_youtube_data.json"

FAISS_INDEX_FILE = "cnas_index"

MAX_CHARS = 2000
BATCH_SIZE = 128


# ─────────────────────────────
# LOAD DATA
# ─────────────────────────────
with open(PDF_CHUNKS_FILE, "r", encoding="utf-8") as f:
    pdf_chunks = json.load(f)

print(f"[+] PDF chunks: {len(pdf_chunks)}")

try:
    with open(YT_CHUNKS_FILE, "r", encoding="utf-8") as f:
        yt_chunks = json.load(f)
    print(f"[+] YouTube chunks: {len(yt_chunks)}")
except FileNotFoundError:
    yt_chunks = []
    print("[!] No YouTube chunks file found, skipping.")


# ─────────────────────────────
# NORMALIZE FUNCTION
# ─────────────────────────────
def normalize_chunk(c, source_type):
    text = c.get("text", "")

    if isinstance(text, list):
        text = " ".join(text)

    text = str(text).strip().replace("\n", " ")[:MAX_CHARS]

    if len(text) < 20:
        return None

    if source_type == "pdf":
        return {
            "text": text,
            "source": c.get("source", "unknown.pdf"),  # e.g. "01.pdf"
            "page": c.get("page", None),
            "source_type": "pdf",
            # YouTube-only fields — null for PDF
            "domain": None,
            "video_id": None,
            "title": None,
        }
    else:
        return {
            "text": text,
            "source": c.get("source", "youtube"),
            "page": None,
            "source_type": "youtube",
            "domain": c.get("domain", None),
            "video_id": c.get("video_id", None),
            "title": c.get("title", None),
        }


# ─────────────────────────────
# MERGE + CLEAN
# ─────────────────────────────
all_chunks = []

for c in pdf_chunks:
    nc = normalize_chunk(c, "pdf")
    if nc:
        all_chunks.append(nc)

for c in yt_chunks:
    nc = normalize_chunk(c, "youtube")
    if nc:
        all_chunks.append(nc)

print(f"[+] Total unified chunks: {len(all_chunks)}")


# ─────────────────────────────
# EXTRACT TEXTS
# ─────────────────────────────
texts = [c["text"] for c in all_chunks]


# ─────────────────────────────
# EMBEDDINGS
# ─────────────────────────────
embedder = OllamaEmbeddings(model="bge-m3")

all_vectors = []

for i in range(0, len(texts), BATCH_SIZE):
    batch = texts[i:i + BATCH_SIZE]
    vecs = embedder.embed_documents(batch)
    all_vectors.extend(vecs)
    print(f"[+] Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")


# ─────────────────────────────
# VECTOR PREP
# ─────────────────────────────
vectors = np.array(all_vectors, dtype="float32")
print(f"[+] Vector shape: {vectors.shape}")
faiss.normalize_L2(vectors)


# ─────────────────────────────
# BUILD FAISS INDEX
# ─────────────────────────────
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)


# ─────────────────────────────
# SAVE INDEX
# ─────────────────────────────
faiss.write_index(index, FAISS_INDEX_FILE + ".bin")

with open(FAISS_INDEX_FILE + "_chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False, indent=2)


# ─────────────────────────────
# DONE
# ─────────────────────────────
print("\n FAISS index built successfully")
print(f" Saved index:  {FAISS_INDEX_FILE}.bin")
print(f" Saved chunks: {FAISS_INDEX_FILE}_chunks.json")