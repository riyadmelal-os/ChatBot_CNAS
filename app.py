import json
import numpy as np
import faiss
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_ollama import OllamaEmbeddings
import google.generativeai as genai
import os
import re

FAISS_INDEX_FILE = "cnas_index.bin"
CHUNKS_FILE = "cnas_index_chunks.json"
TOP_K = 4

index = faiss.read_index(FAISS_INDEX_FILE)

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

embedder = OllamaEmbeddings(model="bge-m3")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD6UkSqkvO-lLTlBPiFBxY5zj-ANaFYvHg")
genai.configure(api_key=GEMINI_API_KEY)

# ── Two separate clients ──────────────────────────────────────────────────────
main_model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction=(
        "Vous êtes un assistant virtuel officiel de la CNAS (Caisse Nationale des Assurances Sociales) en Algérie. "
        "Vous répondez UNIQUEMENT en vous basant sur le contexte documentaire fourni dans chaque message. "
        "Si l'information demandée est inderivable depuis le contexte, répondez: "
        "'Je ne trouve pas cette information dans les documents CNAS.' "
        "Ne jamais inventer ou extrapoler des informations. "
        "répondez en arabe si la question est en arabe. "
        "répondez en français si la question est en français."
    )
)

translate_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=(
        "You are a precise Arabic-to-French translator. "
        "Translate the user's message to French. "
        "Output ONLY the French translation — no explanations, no preamble, no quotation marks."
    )
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_arabic_response(text: str) -> str:
    text = text.replace("\\n", "\n")
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def strip_thinking(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def is_arabic(text: str) -> bool:
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return arabic_chars / max(len(text), 1) > 0.3

def translate_to_french(arabic_text: str) -> str:
    try:
        response = translate_model.generate_content(
            arabic_text,
            generation_config=genai.GenerationConfig(
                max_output_tokens=256,
                temperature=0.1,
            )
        )
        translation = response.text.strip()
        print(f"[Translation] AR → FR: {arabic_text[:80]} → {translation[:80]}")
        return translation
    except Exception as e:
        print(f"[Translation ERROR] Falling back to original query. Reason: {e}")
        return arabic_text


# ── LLM answer generation ─────────────────────────────────────────────────────

def generate_answer(prompt: str) -> str:
    response = main_model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            max_output_tokens=1000000,
            temperature=0.2,
        )
    
    )
    print("RESPOOOOOONSE ///   ",response.text)
    return response.text


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query: str) -> list[str]:
    vec = np.array(embedder.embed_query(query), dtype="float32").reshape(1, -1)
    faiss.normalize_L2(vec)

    distances, I = index.search(vec, TOP_K)

    seen = set()
    results = []

    for rank, (idx, dist) in enumerate(zip(I[0], distances[0])):
        if not (0 <= idx < len(chunks)):
            continue

        neighbor_indices = [idx - 1, idx, idx + 1]

        for neighbor_idx in neighbor_indices:
            if not (0 <= neighbor_idx < len(chunks)):
                continue
            if neighbor_idx in seen:
                continue
            if chunks[neighbor_idx].get("source") != chunks[idx].get("source"):
                continue

            seen.add(neighbor_idx)
            text = chunks[neighbor_idx]["text"]
            source = chunks[neighbor_idx].get("source", "unknown")
            label = "center" if neighbor_idx == idx else "neighbor"
            print(f"[Retrieved #{rank+1} | {label}] score={dist:.4f} | source={source} | preview: {text[:100]}")
            results.append(text)

    return results


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/chat")
def chat(msg: Message):
    original_query = msg.message

    if is_arabic(original_query):
        embedding_query = translate_to_french(original_query)
    else:
        embedding_query = original_query

    context_chunks = retrieve(embedding_query)

    if not context_chunks:
        return {"answer": "Je ne trouve pas cette information dans les documents CNAS."}

    raw_context = "\n\n---\n\n".join(context_chunks)
    CHAR_LIMIT = 3000
    if len(raw_context) > CHAR_LIMIT:
        cutoff = raw_context.find(".", CHAR_LIMIT)
        context = raw_context[:cutoff + 1] if cutoff != -1 else raw_context[:CHAR_LIMIT]
    else:
        context = raw_context

    prompt = f"""Voici des extraits de documents officiels de la CNAS:

===== CONTEXTE =====
{context}
====================
INSTRUCTION: Utilisez UNIQUEMENT les documents ci-dessus pour répondre. Ne dites JAMAIS que vous n'avez pas d'information si elle est présente dans les documents.
En vous basant UNIQUEMENT sur le contexte ci-dessus, répondez à la question suivante:

Question: {original_query}

Réponse:"""

    answer = generate_answer(prompt)
    answer = strip_thinking(answer)
    answer = clean_arabic_response(answer)

    return {"answer": answer}