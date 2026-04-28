import json
import numpy as np
import faiss
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_ollama import OllamaEmbeddings
from huggingface_hub import InferenceClient
import os

FAISS_INDEX_FILE = "cnas_index.bin"
CHUNKS_FILE = "cnas_index_chunks.json"
TOP_K = 5  # increased for better context coverage

# Load index + chunks
index = faiss.read_index(FAISS_INDEX_FILE)

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

# LOCAL embeddings via Ollama
embedder = OllamaEmbeddings(model="nomic-embed-text")

# ONLINE LLM via HuggingFace Inference API
HF_TOKEN = os.environ.get("HF_TOKEN", "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")
MODEL_ID = "google/gemma-4-26B-A4B-it"

client = InferenceClient(
    model=MODEL_ID,
    token=HF_TOKEN
)


def generate_answer(prompt: str) -> str:
    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "Vous êtes un assistant virtuel officiel de la CNAS (Caisse Nationale des Assurances Sociales) en Algérie. "
                    "Vous répondez UNIQUEMENT en vous basant sur le contexte documentaire fourni dans chaque message. "
                    "Si l'information demandée est absente du contexte, répondez: "
                    "'Je ne trouve pas cette information dans les documents CNAS.' "
                    "Ne jamais inventer ou extrapoler des informations. "
                    "Répondez dans la même langue que la question (français ou arabe)."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=600,
        temperature=0.2,  # low temperature = more factual, less creative
    )
    return response.choices[0].message.content


app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str


# ─────────────────────────────
# RETRIEVAL
# ─────────────────────────────
def retrieve(query: str) -> list[str]:
    vec = np.array(embedder.embed_query(query), dtype="float32").reshape(1, -1)
    faiss.normalize_L2(vec)

    distances, I = index.search(vec, TOP_K)

    results = []
    for rank, (idx, dist) in enumerate(zip(I[0], distances[0])):
        if 0 <= idx < len(chunks):
            text = chunks[idx]["text"]
            source = chunks[idx].get("source", "unknown")
            print(f"[Retrieved #{rank+1}] score={dist:.4f} | source={source} | preview: {text[:150]}")
            results.append(text)

    return results


# ─────────────────────────────
# CHAT ENDPOINT
# ─────────────────────────────
@app.post("/chat")
def chat(msg: Message):
    context_chunks = retrieve(msg.message)

    if not context_chunks:
        return {"answer": "Je ne trouve pas cette information dans les documents CNAS."}

    # Build context block — cap at 3000 chars to stay well within token limits
    context = "\n\n---\n\n".join(context_chunks)[:3000]

    prompt = f"""Voici des extraits de documents officiels de la CNAS:

===== CONTEXTE =====
{context}
====================

En vous basant UNIQUEMENT sur le contexte ci-dessus, répondez à la question suivante:

Question: {msg.message}

Réponse:"""

    answer = generate_answer(prompt)

    return {"answer": answer}