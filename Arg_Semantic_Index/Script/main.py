import json
import io
import time
import re
import requests

# --- CONFIGURATION ---
KM_URL       = "http://127.0.0.1:9001"
CONFIG_PATH  = "final_processed_config_unencrypted.json"
ASK_QUESTION = "What is a key argument of the discourse in this source?"
SEARCH_QUERY = "key argument"  # terms to semantically search for

# --- SNIPPET CLEANUP ---
def clean_snippet(text: str, maxlen: int = 200) -> str:
    """
    Trim a snippet to word boundaries within maxlen.
    """
    # take up to maxlen chars
    snippet = text[:maxlen]
    # drop partial leading word
    snippet = re.sub(r"^\S*", "", snippet)
    # drop partial trailing word
    parts = snippet.rsplit(' ', 1)
    return parts[0] if len(parts) > 1 else snippet

# --- UPLOAD ---
def upload_source(src: dict):
    doc_id   = src["id"]
    file_obj = io.BytesIO(src["full_text"].encode("utf-8"))
    files    = {"file1": (f"{doc_id}.txt", file_obj)}
    data     = {
        "documentId": doc_id,
        "tags": [
            f"source_name:{src['source_name']}",
            f"source_type:{src['source_type']}"
        ]
    }
    resp = requests.post(f"{KM_URL}/upload", files=files, data=data)
    resp.raise_for_status()
    print(f"[UPLOAD] {doc_id} → {resp.json()}")

# --- STATUS CHECK ---
def wait_for_upload(doc_id: str, timeout: int = 60, poll_interval: float = 2.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r    = requests.get(f"{KM_URL}/upload-status", params={"documentId": doc_id})
        r.raise_for_status()
        info = r.json()
        done = info.get("completed", False)
        rem  = info.get("remaining_steps", [])
        idx  = info.get("index", "default")
        print(f"[STATUS] {doc_id}: completed={done}, remaining={rem}")
        if done:
            return idx
        time.sleep(poll_interval)
    raise RuntimeError(f"Timeout waiting for upload-status of {doc_id}")

# --- ASK REQUEST ---
def ask_source(src_name: str, index: str, question: str,
               retries: int = 10, delay: float = 2.0) -> dict:
    payload = {
        "index":   index,
        "question": question,
        "filters": [
            {"source_name": [src_name]}
        ]
    }
    for attempt in range(1, retries + 1):
        r = requests.post(f"{KM_URL}/ask", json=payload)
        r.raise_for_status()
        body = r.json()
        if body.get("text") or body.get("results") or body.get("hits"):
            return body
        print(f"[ASK:{src_name}] try {attempt}: no answer, retrying in {delay}s…")
        time.sleep(delay)
    raise RuntimeError(f"No answer for {src_name} after {retries} retries")

# --- SEARCH REQUEST ---
def search_source(src_name: str, index: str, query: str,
                  limit: int = 5, retries: int = 5, delay: float = 1.0) -> dict:
    payload = {
        "index":   index,
        "query":   query,
        "filters": [
            {"source_name": [src_name]}
        ],
        "limit":   limit
    }
    for attempt in range(1, retries + 1):
        r = requests.post(f"{KM_URL}/search", json=payload)
        r.raise_for_status()
        body = r.json()
        if body.get("results"):
            return body
        print(f"[SEARCH:{src_name}] try {attempt}: no hits, retrying in {delay}s…")
        time.sleep(delay)
    raise RuntimeError(f"No search results for {src_name} after {retries} retries")

# --- MAIN FLOW ---
if __name__ == "__main__":
    # Load config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    for src in sources:
        doc_id   = src["id"]
        src_name = src["source_name"]

        # Upload & wait
        upload_source(src)
        index_name = wait_for_upload(doc_id)

        # Ask
        print(f"\n--- ASK RESULT for {doc_id} ---")
        ask_resp = ask_source(src_name, index_name, ASK_QUESTION)
        if "text" in ask_resp:
            print(ask_resp["text"])
        elif "results" in ask_resp:
            for hit in ask_resp["results"]:
                print(" •", hit.get("text") or hit.get("snippet", ""))
        else:
            print(ask_resp)

        # Search
        print(f"\n--- SEARCH RESULTS for {doc_id} ---")
        search_resp = search_source(src_name, index_name, SEARCH_QUERY, limit=3)
        for i, result in enumerate(search_resp["results"], start=1):
            print(f"Result #{i}: documentId={result.get('documentId')}, index={result.get('index')}")
            for j, part in enumerate(result.get("partitions", []), start=1):
                raw_text = part.get("text", "").replace("\n", " ").strip()
                text     = clean_snippet(raw_text, maxlen=200)
                relevance= part.get("relevance", 0)
                print(f"  {i}.{j}. “{text}…” (relevance={relevance:.3f})")
            print()
