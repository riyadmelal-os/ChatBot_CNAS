import os
import json
import pdfplumber
import hashlib
from datetime import datetime

PDF_FOLDER = "cnas_files"
OUTPUT_FILE = "chunks.json"

CHUNK_SIZE = 400
OVERLAP = 50


# ─── TEXT CLEANING ─────────────────────────────

def clean_text(text):
    lines = text.split("\n")
    lines = [l.strip() for l in lines if len(l.strip()) > 20]
    return " ".join(lines)


# ─── CHUNKING ──────────────────────────────────

def chunk_text(text):
    words = text.split()
    chunks = []
    i = 0

    while i < len(words):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += CHUNK_SIZE - OVERLAP

    return chunks


# ─── PDF READER ────────────────────────────────

def extract_pdf_text(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ─── LOAD EXISTING JSON ────────────────────────

def load_existing():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ─── SAVE JSON ─────────────────────────────────

def save_all(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── ID ────────────────────────────────────────

def make_id(file, index):
    h = hashlib.md5(file.encode()).hexdigest()[:8]
    return f"pdf_{h}_{index}"


# ─── MAIN PROCESS ──────────────────────────────

def process_pdfs():
    all_data = load_existing()
    existing_ids = {item.get("id") for item in all_data}

    print(f"[+] Loaded {len(all_data)} existing chunks")

    for file in os.listdir(PDF_FOLDER):
        if not file.lower().endswith(".pdf"):
            continue

        path = os.path.join(PDF_FOLDER, file)
        print(f"[+] Processing {file}")

        try:
            text = extract_pdf_text(path)
            text = clean_text(text)
            chunks = chunk_text(text)

            added = 0

            for i, chunk in enumerate(chunks):
                if len(chunk) < 50:
                    continue

                cid = make_id(file, i)

                # avoid duplicates
                if cid in existing_ids:
                    continue

                all_data.append({
                    "id": cid,
                    "text": chunk,
                    "source": file,
                    "domain": "pdf",
                    "scraped_at": datetime.utcnow().isoformat()
                })

                existing_ids.add(cid)
                added += 1

            print(f"    → +{added} chunks")

        except Exception as e:
            print(f"[ERROR] {file}: {e}")

    save_all(all_data)

    print(f"[OK] Done. Total chunks: {len(all_data)} -> {OUTPUT_FILE}")


# ─── RUN ───────────────────────────────────────

if __name__ == "__main__":
    process_pdfs()