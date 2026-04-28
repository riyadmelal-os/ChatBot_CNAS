from pdf2image import convert_from_path
import pytesseract
import sys
sys.stdout.reconfigure(encoding='utf-8')

# If you're on Windows, set this path:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

images = convert_from_path(
    "C:/Users/riyad/Pictures/RAG/cnas_files/6_06-07.pdf",
    poppler_path=r"C:\Users\riyad\Downloads\poppler-25.12.0\Library\bin"
)

text = ""

for i, img in enumerate(images):
    page_text = pytesseract.image_to_string(img, lang="fra+ara")  # use "fra" or "ara" if needed
    print(f"--- Page {i+1} ---")
    print(page_text)
    text += page_text + "\n"

# Save result
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(text)