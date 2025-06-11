import json
from km_client import (
    format_doc_id, upload_source, wait_for_upload,
    ask_source, search_source, clean_snippet
)

CONFIG_PATH = "data/final_processed_config_unencrypted.json"
ASK_QUESTION = "What is a key argument of the discourse in this source?"
SEARCH_QUERY = "key argument"


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # Combine first two sources into one document
    combined = {
        "source_name": sources[0]["source_name"],
        "source_type": sources[0]["source_type"],
        "full_text": sources[0]["full_text"] + "\n" + sources[1]["full_text"]
    }
    remaining = sources[2:]

    for src in [combined] + remaining:
        doc_info = upload_source(src)
        doc_id = doc_info["doc_id"]
        print(f"[UPLOAD] {doc_id} → {doc_info['response']}")
        index = wait_for_upload(doc_id)

        print(f"\n--- ASK RESULT for {doc_id} ---")
        ask_resp = ask_source(src["source_name"], index, ASK_QUESTION)
        if "text" in ask_resp:
            print(ask_resp["text"])
        else:
            for hit in ask_resp.get("results", []):
                print(" •", hit.get("text", hit.get("snippet", "")))

        print(f"\n--- SEARCH RESULTS for {doc_id} ---")
        search_resp = search_source(src["source_name"], index, SEARCH_QUERY, limit=3)
        for i, result in enumerate(search_resp["results"], start=1):
            print(f"Result #{i}: documentId={result.get('documentId')}, index={result.get('index')}")
            for j, part in enumerate(result.get("partitions", []), start=1):
                raw = part.get("text", "").replace("\n", " ").strip()
                text = clean_snippet(raw)
                rel = part.get("relevance", 0)
                print(f" {i}.{j}. “{text}…” (relevance={rel:.3f})")
            print()


if __name__ == "__main__":
    main()
