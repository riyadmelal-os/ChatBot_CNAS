from PyPDF2 import PdfReader

reader = PdfReader("C:/Users/riyad/Downloads/15_90-11.pdf")

text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

print(text)