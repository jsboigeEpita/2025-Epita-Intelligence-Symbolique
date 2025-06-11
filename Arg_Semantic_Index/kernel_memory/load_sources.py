import json
from km_client import (
    format_doc_id, upload_source, wait_for_upload,
    ask_source, search_source, clean_snippet
)

CONFIG_PATH = "sources/final_processed_config_unencrypted.json"


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

        print(f"Uploaded document ID: {format_doc_id(doc_id)}")
    print("\nAll documents uploaded successfully.")

if __name__ == "__main__":
    main()
