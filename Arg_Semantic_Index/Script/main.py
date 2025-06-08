import requests
import time

# Base URL of your running Kernel Memory service
KM_URL = "http://127.0.0.1:9001"
DOC_ID = "config_semantic_01"

def upload_config():
    files = {
        "file1": (
            "final_processed_config_unencrypted.json",
            open("final_processed_config_unencrypted.json", "rb"),
        )
    }
    data = {
        "documentId": DOC_ID,
        "tags": [
            "type:config",
            "purpose:semantic-analysis"
        ],
    }
    r = requests.post(f"{KM_URL}/upload", files=files, data=data)
    r.raise_for_status()
    print("Upload response:", r.json())

def ask_with_retry(question: str,
                   retries: int = 10,
                   delay: float = 2.0):
    """
    Repeatedly POST to /ask until we get non-empty response or exhaust retries.
    """
    # Build the payload with:
    #  • "question"  — the free-form prompt
    #  • "filters"   — only return memories tagged type:config
    payload = {
        "question": question,
        "filters": [
            { "type": ["config"] }
        ]
    }

    for attempt in range(1, retries + 1):
        resp = requests.post(f"{KM_URL}/ask", json=payload)
        if resp.status_code == 200:
            body = resp.json()
            # the Python example returns its answer in "text"
            if body.get("text"):
                return body
        else:
            print(f"Attempt {attempt}: HTTP {resp.status_code}")
        print(f"Attempt {attempt}: no memories yet, retrying in {delay}s…")
        time.sleep(delay)

    raise RuntimeError(f"No answer after {retries} attempts.")

def main():
    # 1) Upload your config
    upload_config()

    # 2) Ask, retrying until ingestion has materialized
    question = "Donne un argument que propose LFI"
    answer = ask_with_retry(question)

    # 3) Print out the final answer
    print("\nQuestion: " + question)
    print("\nAnswer:")
    print(answer["text"])

if __name__ == "__main__":
    main()
