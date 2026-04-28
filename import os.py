import requests
from bs4 import BeautifulSoup
import json
import time
import hashlib
from urllib.parse import urljoin, urlparse
from datetime import datetime
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ─── CONFIG ───────────────────────────────────────────────────────────────────

START_URLS = [
    "https://cnas.dz/fr/",
    "https://www.travail.gov.dz",
    "https://www.ilo.org/algerie",
    "https://damancom.casnos.dz/?returnUrl=home",
    "https://fr.wikipedia.org/wiki/Caisse_nationale_de_s%C3%A9curit%C3%A9_sociale_des_non-salari%C3%A9s",
    "https://fr.wikipedia.org/wiki/Caisse_nationale_des_assurances_sociales",
    "https://www.cnac.dz/fr/regime-dassurance-chomage",
    "https://www.cnac.dz/Fr/accueil",
    "https://cnas.dz/fr/assurance-maladie/",
    "https://cnas.dz/fr/direction-des-prestations/",
    "https://cnas.dz/fr/assurance-maternite/",
    "https://cnas.dz/fr/assurance-invalidite/",
    "https://cnas.dz/fr/les-allocations-familiales/",
    "https://cnas.dz/fr/accidents-du-travail-et-maladie-proffesionelle/",
    "https://cnas.dz/fr/assurance-deces/",
    "https://cnas.dz/fr/employeur/",
    "https://cnas.dz/fr/assures/",
]

MAX_PAGES   = 200
DELAY       = 1.5
OUTPUT_FILE = "dataset.json"
CHUNK_SIZE  = 400
OVERLAP     = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CNASResearchBot/1.0)"
}

# ─── HELPERS ──────────────────────────────────────────────────────────────────

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


def extract_text(soup):
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def make_id(url, index):
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"scraped_{h}_{index}"


def get_domain(url):
    return urlparse(url).netloc


def normalize_url(url):
    url = url.split("#")[0]
    return url.rstrip("/")


# ─── SCRAPER ──────────────────────────────────────────────────────────────────

def scrape_all():

    # Load existing dataset if exists
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            all_chunks = json.load(f)
        print(f"[+] Loaded {len(all_chunks)} existing chunks\n")
    except FileNotFoundError:
        all_chunks = []
        print("[+] Starting fresh\n")

    existing_ids = {c.get("id") for c in all_chunks if isinstance(c, dict)}

    visited   = set()
    to_visit  = [normalize_url(u) for u in START_URLS]
    page_count = 0

    while to_visit and page_count < MAX_PAGES:

        url = to_visit.pop(0)
        url = normalize_url(url)

        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()

            if "html" not in resp.headers.get("Content-Type", ""):
                continue

        except Exception as e:
            print(f"[{page_count+1}] {url} → ERROR: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        text = extract_text(soup)

        # ─── SAVE ALL TEXT (NO KEYWORD FILTER) ───
        new = 0

        for i, chunk in enumerate(chunk_text(text)):

            chunk_id = make_id(url, i)

            if chunk_id in existing_ids:
                continue

            all_chunks.append({
                "id": chunk_id,
                "text": chunk,
                "source": url,
                "domain": get_domain(url),
                "page": page_count,
                "scraped_at": datetime.utcnow().isoformat()
            })

            existing_ids.add(chunk_id)
            new += 1

        print(f"[{page_count+1}] {url} → +{new} chunks")

        # ─── DISCOVER NEW LINKS ───
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            href = normalize_url(href)

            if href.startswith("http") and href not in visited:
                to_visit.append(href)

        page_count += 1
        time.sleep(DELAY)

    # Save dataset
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] {len(all_chunks)} total chunks saved to {OUTPUT_FILE}")


# ─── ENTRY ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== FULL WEB SCRAPER (NO FILTERING) ===")
    print(f"Max pages: {MAX_PAGES}\n")
    scrape_all()