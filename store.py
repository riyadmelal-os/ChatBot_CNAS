import os
from pdf2image import convert_from_path
import pytesseract
import json
import re

# --- CONFIG ---
PDF_FOLDER = "cnas_files"
POPPLER_PATH = r"C:/Users/riyad/Downloads/poppler-25.12.0/Library/bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DATASET_FILE = "dataset.json"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# --- clean text ---
def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# --- chunk text ---
def chunk_text(text, chunk_size=300):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# --- load existing dataset (append mode) ---
if os.path.exists(DATASET_FILE):
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            data = []
else:
    data = []

existing_entries = set(
    (item["text"], item.get("source"), item.get("page"))
    for item in data
)

# --- process PDFs ---
for file_name in os.listdir(PDF_FOLDER):
    if not file_name.lower().endswith(".pdf"):
        continue

    pdf_path = os.path.join(PDF_FOLDER, file_name)
    print(f"Processing: {file_name}")

    images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

    for page_num, img in enumerate(images, start=1):
        raw_text = pytesseract.image_to_string(img, lang="fra+ara")

        cleaned = clean_text(raw_text)
        chunks = chunk_text(cleaned)

        for chunk in chunks:
            entry = (chunk, file_name, page_num)

            # avoid duplicates
            if entry in existing_entries:
                continue

            data.append({
                "text": chunk,
                "source": file_name,
                "page": page_num
            })

            existing_entries.add(entry)

# --- save JSON ---
with open(DATASET_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nDataset now contains {len(data)} chunks.")