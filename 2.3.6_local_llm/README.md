# IASY 2025: Local LLM Fallacy Detection API

## Setup

To create a Python virtual environment and download the necessary local LLM models, please run the setup script:

```sh
./setup.sh
```

---

## OpenAI-Compatible API

We provide an API compatible with the OpenAI format using `FastAPI`. To run the server locally and listen on port 8000, use the following command:

```sh
uvicorn app:app
```

> **Note:**  
> During development, you can add the `--reload` flag to automatically reload the server whenever you make changes to your code:

```sh
uvicorn app:app --reload
```

---

## Usage

After starting the server, you can query the API to get a fallacy report. The API expects requests in the OpenAI request format at the `/v1/fallacy-detection` endpoint.

### Example request using `curl`:

```sh
curl -X POST \
  http://127.0.0.1:8000/v1/fallacy-detection \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Llama3_8B_Q6",
    "input": "Vaccines are dangerous because my neighbor experienced side effects after his vaccination. Furthermore, pharmaceutical companies are only interested in making a profit. Therefore, we should not trust vaccines."
  }'
```

---
