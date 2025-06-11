# 🧠 Semantic Index of Arguments

This project focuses on semantic indexing of arguments from large historical texts and political speeches (e.g., Lincoln-Douglas debates). It allows users to search and ask questions over the content using OpenAI embeddings, leveraging [Kernel Memory](https://github.com/microsoft/kernel-memory) as the semantic search engine.

## 🔧 Features

- 🔍 Semantic search across historical speeches
- 🤖 RAG-based question answering using contextual document retrieval
- 🧠 Automatic indexing with OpenAI embeddings
- 🖥️ Interactive demo interface built with Streamlit (`UI_streamlit.py`)

---

## ⚙️ Requirements

- Python 3.8+
- Valid OpenAI API Key (**required**)
- Docker installed

---

## 📦 Installation

1. **Clone the repository:**

   ```bash
   git clone <REPO_URL>
   cd Arg_Semantic_Index
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate     # On Windows: .\venv\Scripts\activate
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Run Kernel Memory with Docker

> **⚠️ IMPORTANT:** You must insert your OpenAI API key in `appsettings.Development.json` before starting.

Use the following Docker command to start the Kernel Memory service:

```bash
docker run --volume ./kernel_memory/appsettings.Development.json:/app/appsettings.Production.json \
           -it --rm -p 9001:9001 kernelmemory/service
```

This starts the Kernel Memory API on `http://localhost:9001`.

---

## 🧠 Load Documents into Kernel Memory

Once Kernel Memory is running, ingest the data using:

```bash
python kernel_memory/load_sources.py
```

---

## 💻 Launch the Streamlit Interface

```bash
streamlit run UI_streamlit.py
```

Open your browser to [http://localhost:8501](http://localhost:8501) to interact with the app.

---

## 🔑 OpenAI API Key Configuration

To use OpenAI embeddings, you must provide your API key in the file:  
`kernel_memory/appsettings.Development.json`

Example structure:

```json
{
  "KernelMemory": {
    "Embedding": {
      "Service": "openai",
      "Model": "text-embedding-ada-002",
      "ApiKey": "YOUR_OPENAI_API_KEY_HERE"
    }
  }
}
```

---

## 📁 Project Structure

```
Arg_Semantic_Index
├── kernel_memory/
│   ├── appsettings.Development.json     ← Add your OpenAI API key here
│   ├── example.py                       ← Example usage of Kernel Memory
│   ├── km_client.py                     ← API wrapper for KM
│   └── load_sources.py                  ← Loads and ingests discourse data
├── prompts.txt
├── README.md
├── requirements.txt
├── sources/
│   └── final_processed_config_unencrypted.json  ← Cleaned discourse dataset
└── UI_streamlit.py                    ← Streamlit user interface
```

---

## 👥 Authors

- yanis.martin
- leo.lopes