import json

OLD_FILE = "dataset2.json"
DATASET_FILE = "dataset.json"

# --- load old data ---
with open(OLD_FILE, "r", encoding="utf-8") as f:
    old_data = json.load(f)

# --- load existing dataset ---
try:
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
except:
    dataset = []

# --- convert and append ---
for i, item in enumerate(old_data):

    text = item.get("text", "")  # ✅ FIX HERE

    if not text or len(text.strip()) < 20:
        continue

    dataset.append({
        "text": text.strip(),
        "source": item.get("source", "old.json"),
        "page": item.get("page", None),
        "id": item.get("id", f"old_{i}")
    })

# --- save updated dataset ---
with open(DATASET_FILE, "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"Added {len(old_data)} entries. Total now: {len(dataset)}")