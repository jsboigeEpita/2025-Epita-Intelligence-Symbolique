import io
import time
import re
import unicodedata
import requests

KM_URL = "http://127.0.0.1:9001"


def format_doc_id(source_name: str) -> str:
    """
    Generate an ASCII-only document ID from source_name by removing accents,
    replacing non-word characters with underscores, and lowercasing.
    """
    normalized = unicodedata.normalize('NFKD', source_name)
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r"\W+", "_", ascii_name)
    return slug.strip('_').lower()


def upload_source(src: dict) -> dict:
    """
    Uploads one source to Kernel Memory and returns a dict containing:
      - doc_id: formatted document ID
      - response: upload response JSON
    """
    doc_id = format_doc_id(src["source_name"])
    file_obj = io.BytesIO(src["full_text"].encode("utf-8"))
    files = {"file1": (f"{doc_id}.txt", file_obj)}
    data = {
        "documentId": doc_id,
        "tags": [
            f"source_name:{src['source_name']}",
            f"source_type:{src['source_type']}"
        ]
    }
    resp = requests.post(f"{KM_URL}/upload", files=files, data=data)
    resp.raise_for_status()
    return {"doc_id": doc_id, "response": resp.json()}


def wait_for_upload(doc_id: str, timeout: int = 60000, poll_interval: float = 2.0) -> str:
    """
    Polls GET /upload-status until completed=True and returns the index name.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{KM_URL}/upload-status", params={"documentId": doc_id})
        r.raise_for_status()
        info = r.json()
        if info.get("completed", False):
            return info.get("index", "default")
        time.sleep(poll_interval)
    raise RuntimeError(f"Timeout waiting for upload-status of {doc_id}")


def ask_source(src_name: str, index: str, question: str,
               retries: int = 10, delay: float = 2.0) -> dict:
    """
    Submits an /ask request filtered by source_name until a non-empty answer is returned.
    """
    payload = {
        "index": index,
        "question": question,
        "filters": [{"source_name": [src_name]}]
    }
    for attempt in range(retries):
        r = requests.post(f"{KM_URL}/ask", json=payload)
        r.raise_for_status()
        body = r.json()
        if body.get("text") or body.get("results") or body.get("hits"):
            return body
        time.sleep(delay)
    raise RuntimeError(f"No answer for {src_name}")


def search_source(src_name: str, index: str, query: str,
                  limit: int = 5, retries: int = 5, delay: float = 1.0) -> dict:
    """
    Submits a /search request filtered by source_name until results are returned.
    """
    payload = {
        "index": index,
        "query": query,
        "filters": [{"source_name": [src_name]}],
        "limit": limit
    }
    for attempt in range(retries):
        r = requests.post(f"{KM_URL}/search", json=payload)
        r.raise_for_status()
        body = r.json()
        if body.get("results"):
            return body
        time.sleep(delay)
    raise RuntimeError(f"No search results for {src_name}")


def clean_snippet(text: str, maxlen: int = 1000) -> str:
    """
    Trim a snippet to word boundaries within maxlen.
    """
    snippet = text[:maxlen]
    snippet = re.sub(r"^\S*", "", snippet)
    parts = snippet.rsplit(' ', 1)
    return parts[0] if len(parts) > 1 else snippet
