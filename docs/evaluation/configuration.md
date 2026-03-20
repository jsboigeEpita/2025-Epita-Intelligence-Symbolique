# Evaluation Framework Configuration Guide

Setup and configuration for the evaluation framework.

## Table of Contents

- [Environment Setup](#environment-setup)
- [Model Configuration](#model-configuration)
- [Dataset Configuration](#dataset-configuration)
- [Corpus Metadata](#corpus-metadata)
- [Workflow Configuration](#workflow-configuration)
- [Advanced Configuration](#advanced-configuration)

---

## Environment Setup

### Required Environment Variables

```bash
# OpenAI-compatible API configuration
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL_ID=gpt-5-mini

# Alternative: OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Optional: GitHub CLI

```bash
# For GitHub integration (optional)
GH_TOKEN=ghp_...
```

### Environment File Template

Create a `.env` file in the project root:

```bash
# Copy the example template
cp .env.example .env

# Edit with your values
nano .env
```

Example `.env` file:

```bash
# ============================================================
# LLM API Configuration
# ============================================================

# OpenAI (default provider)
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL_ID=gpt-5-mini

# Alternative: OpenRouter
# OPENROUTER_API_KEY=sk-or-your-key-here
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ============================================================
# GitHub Integration (optional)
# ============================================================
GH_TOKEN=ghp_your_github_token_here

# ============================================================
# Evaluation Settings
# ============================================================
EVALUATION_TIMEOUT=120
EVALUATION_MAX_TEXT_CHARS=5000
EVALUATION_RESULTS_DIR=argumentation_analysis/evaluation/results
```

---

## Model Configuration

### Default Model Registry

The framework creates a default model registry from environment variables:

```python
from argumentation_analysis.evaluation.model_registry import ModelRegistry

# Auto-loads from OPENAI_* environment variables
registry = ModelRegistry.from_env()
```

### Registering Custom Models

```python
from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig

# Create registry with default config
default_config = ModelConfig(
    model_id="gpt-5-mini",
    base_url="https://api.openai.com/v1",
    api_key_env_var="OPENAI_API_KEY",
    display_name="GPT-5 Mini",
    cost_per_1k_tokens=0.0001,
)

registry = ModelRegistry(default_config=default_config, models={})

# Register additional models
registry.register("gpt4", ModelConfig(
    model_id="gpt-4-turbo",
    base_url="https://api.openai.com/v1",
    api_key_env_var="OPENAI_API_KEY",
    display_name="GPT-4 Turbo",
    cost_per_1k_tokens=0.01,
    is_thinking_model=False,
    max_tokens=128000,
))

registry.register("claude", ModelConfig(
    model_id="claude-3-opus-20240229",
    base_url="https://api.anthropic.com/v1",
    api_key_env_var="ANTHROPIC_API_KEY",
    display_name="Claude 3 Opus",
    cost_per_1k_tokens=0.015,
    is_thinking_model=False,
    max_tokens=200000,
))

registry.register("local", ModelConfig(
    model_id="llama-3-70b",
    base_url="http://localhost:8000/v1",
    api_key_env_var="LOCAL_API_KEY",
    display_name="Llama 3 70B (Local)",
    cost_per_1k_tokens=0.0,
    is_thinking_model=False,
    max_tokens=8192,
))
```

### Model Switching

```python
# Save current environment
saved_env = registry.save_env()

# Switch to different model
registry.activate("gpt4")

# Run inference...

# Restore original environment
registry.restore_env(saved_env)
```

### Popular Model Configurations

#### GPT Models

```python
# GPT-5 Mini (fast, cost-effective)
ModelConfig(
    model_id="gpt-5-mini",
    base_url="https://api.openai.com/v1",
    api_key_env_var="OPENAI_API_KEY",
    display_name="GPT-5 Mini",
    cost_per_1k_tokens=0.0001,
    max_tokens=128000,
)

# GPT-4 Turbo (capable)
ModelConfig(
    model_id="gpt-4-turbo",
    base_url="https://api.openai.com/v1",
    api_key_env_var="OPENAI_API_KEY",
    display_name="GPT-4 Turbo",
    cost_per_1k_tokens=0.01,
    max_tokens=128000,
)
```

#### Claude Models

```python
# Claude 3 Opus (high quality)
ModelConfig(
    model_id="claude-3-opus-20240229",
    base_url="https://api.anthropic.com/v1",
    api_key_env_var="ANTHROPIC_API_KEY",
    display_name="Claude 3 Opus",
    cost_per_1k_tokens=0.015,
    max_tokens=200000,
)

# Claude 3 Sonnet (balanced)
ModelConfig(
    model_id="claude-3-sonnet-20240229",
    base_url="https://api.anthropic.com/v1",
    api_key_env_var="ANTHROPIC_API_KEY",
    display_name="Claude 3 Sonnet",
    cost_per_1k_tokens=0.003,
    max_tokens=200000,
)
```

#### Local Models (Ollama/vLLM)

```python
# Local Llama 3
ModelConfig(
    model_id="llama-3-70b",
    base_url="http://localhost:11434/v1",  # Ollama default
    api_key_env_var="OLLAMA_API_KEY",  # Can be dummy value
    display_name="Llama 3 70B (Local)",
    cost_per_1k_tokens=0.0,
    max_tokens=8192,
)
```

---

## Dataset Configuration

### Dataset Format

Datasets are JSON files with the following structure:

```json
{
  "version": "1.0",
  "name": "Baseline Corpus v1",
  "description": "Baseline evaluation corpus for argumentation analysis",
  "documents": [
    {
      "id": "doc_001",
      "name": "Political Speech Sample",
      "source": "https://example.com/speech1",
      "difficulty": "medium",
      "expected_fallacies": ["appeal_to_emotion", "straw_man"],
      "expected_quality_score_range": [3, 6],
      "language": "fr",
      "domain": "politics",
      "full_text": "Complete document text here...",
      "extracts": [
        {
          "id": "ext_001",
          "extract_text": "Specific text segment...",
          "speaker": "John Doe",
          "timestamp": "00:01:23"
        }
      ]
    }
  ]
}
```

### Document Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique document identifier |
| `name` | string | Yes | Human-readable document name |
| `difficulty` | string | No | `easy`, `medium`, or `hard` |
| `expected_fallacies` | list | No | Expected fallacy types |
| `expected_quality_score_range` | list | No | Min/max expected quality (0-10) |
| `full_text` | string | Yes* | Complete document text |
| `extracts` | list | No | Text extracts with metadata |

*Either `full_text` or `extracts` must be provided.

### Loading Datasets

```python
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkRunner

runner = BenchmarkRunner(model_registry)

# Unencrypted dataset
runner.load_dataset_unencrypted("corpus.json")

# Encrypted dataset (Fernet + gzip)
runner.load_dataset_encrypted("corpus.enc", "passphrase")

# Access documents
for idx in range(len(runner.dataset)):
    text = runner.get_document_text(idx)
    name = runner.get_document_name(idx)
    print(f"{idx}: {name} ({len(text)} chars)")
```

### Creating Encrypted Datasets

```python
import json
import gzip
from argumentation_analysis.core.utils.crypto_utils import (
    derive_encryption_key,
    encrypt_data_with_fernet,
)

# Load corpus
with open("corpus.json", "r") as f:
    corpus_data = json.load(f)

# Compress
json_bytes = json.dumps(corpus_data).encode('utf-8')
compressed = gzip.compress(json_bytes)

# Encrypt
key = derive_encryption_key("your-passphrase")
encrypted = encrypt_data_with_fernet(compressed, key)

# Save
with open("corpus.enc", "wb") as f:
    f.write(encrypted)
```

---

## Corpus Metadata

### Corpus File Structure

The corpus metadata file (`baseline_corpus_v1.json`) provides:

```json
{
  "version": "1.0",
  "name": "Baseline Corpus v1",
  "description": "Baseline evaluation corpus",
  "documents": [
    {
      "id": "doc_001",
      "difficulty": "easy",
      "expected_fallacies": ["ad_hominem"],
      "expected_quality_score_range": [7, 9],
      "domain": "politics",
      "language": "fr"
    }
  ]
}
```

### Difficulty Levels

| Level | Description | Characteristics |
|-------|-------------|------------------|
| `easy` | Simple arguments | Clear structure, obvious fallacies, short text |
| `medium` | Moderate complexity | Mixed fallacy types, some nuance |
| `hard` | Complex arguments | Subtle reasoning, multiple embedded fallacies |

### Fallacy Categories

Supported expected fallacy types (from taxonomy):

- `ad_hominem` - Personal attacks
- `appeal_to_authority` - Argument from authority
- `appeal_to_emotion` - Emotional manipulation
- `appeal_to_popularity` - Bandwagon fallacy
- `appeal_to_tradition` - Traditional wisdom
- `false_analogy` - Incorrect comparison
- `false_dilemma` - False dichotomy
- `guilt_by_association` - Association fallacy
- `hasty_generalization` - Overgeneralization
- `loaded_language` - Emotional language
- `poisoning_the_well` - Preemptive discredit
- `red_herring` - Irrelevant distraction
- `slippery_slope` - Exaggerated consequences
- `straw_man` - Misrepresentation

---

## Workflow Configuration

### Workflow Definitions

```python
from argumentation_analysis.orchestration.unified_pipeline import (
    UnifiedPipeline,
)

# Pre-configured workflows
WORKFLOWS = {
    "light": ["extract", "quality", "counter"],
    "standard": ["extract", "quality", "counter", "jtms", "governance", "debate"],
    "full": ["transcribe", "extract", "quality", "neural_fallacy", "counter",
             "jtms", "governance", "debate", "index"],
}
```

### Workflow Phase Details

| Phase | Description | Optional | Dependencies |
|-------|-------------|----------|--------------|
| `transcribe` | Speech-to-text conversion | Yes | None |
| `extract` | Fact/claim extraction | No | None |
| `quality` | Argument quality evaluation | No | extract |
| `neural_fallacy` | Neural fallacy detection | Yes | extract |
| `counter` | Counter-argument generation | No | extract, quality |
| `jtms` | Belief maintenance | Yes | extract |
| `governance` | Governance simulation | Yes | extract |
| `debate` | Adversarial debate | Yes | extract |
| `index` | Semantic indexing | Yes | All phases |

### Custom Workflow Creation

```python
from argumentation_analysis.evaluation.model_registry import ModelRegistry
from argumentation_analysis.orchestration.unified_pipeline import UnifiedPipeline

# Create custom workflow
pipeline = UnifiedPipeline()

# Define custom phases
custom_workflow = [
    ("extract", "argumentation_extraction", {}),
    ("quality", "argument_quality", {}),
    ("counter", "counter_argument", {}),
    ("debate", "adversarial_debate", {"turns": 3}),
]

# Register custom workflow
pipeline.register_workflow("custom_debate", custom_workflow)

# Run with custom workflow
result = await run_unified_analysis(
    text="Argument text...",
    workflow_name="custom_debate",
)
```

---

## Advanced Configuration

### Timeout Configuration

```python
# Global timeout (applies to all operations)
import os
os.environ["EVALUATION_TIMEOUT"] = "180"  # 3 minutes

# Per-cell timeout
result = await runner.run_cell(
    workflow_name="full",
    model_name="default",
    document_index=0,
    timeout=300.0,  # 5 minutes for this cell
)
```

### Text Length Limits

```python
# Global text limit
os.environ["EVALUATION_MAX_TEXT_CHARS"] = "10000"

# Per-cell text limit
result = await runner.run_cell(
    workflow_name="standard",
    model_name="default",
    document_index=0,
    max_text_chars=3000,  # Truncate to 3000 chars
)
```

### Results Directory

```python
from pathlib import Path
from argumentation_analysis.evaluation.result_collector import ResultCollector

# Custom results directory
custom_dir = Path("custom_benchmark_results")
collector = ResultCollector(custom_dir)

# Or set via environment
os.environ["EVALUATION_RESULTS_DIR"] = "custom_results"
```

### Logging Configuration

```python
import logging

# Configure evaluation logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("evaluation.log"),
        logging.StreamHandler(),
    ],
)

# Specific component logging
logger = logging.getLogger("evaluation.benchmark_runner")
logger.setLevel(logging.DEBUG)

judge_logger = logging.getLogger("evaluation.judge")
judge_logger.setLevel(logging.WARNING)
```

### Concurrency Control

```python
import asyncio

# Sequential execution (default)
result = await runner.run_cell(...)  # One at a time

# Parallel execution
tasks = [
    runner.run_cell("light", "default", i)
    for i in range(10)
]
results = await asyncio.gather(*tasks)

# Controlled parallelism
semaphore = asyncio.Semaphore(3)  # Max 3 concurrent

async def run_with_limit(runner, workflow, model, idx):
    async with semaphore:
        return await runner.run_cell(workflow, model, idx)

tasks = [
    run_with_limit(runner, "light", "default", i)
    for i in range(10)
]
results = await asyncio.gather(*tasks)
```

---

## Validation and Testing

### Validate Dataset

```python
def validate_dataset(corpus_path: str) -> bool:
    """Validate dataset format and content."""

    import json

    with open(corpus_path, "r") as f:
        corpus = json.load(f)

    # Check required fields
    assert "documents" in corpus, "Missing documents field"
    assert isinstance(corpus["documents"], list), "Documents must be a list"

    # Check each document
    for doc in corpus["documents"]:
        assert "id" in doc, f"Document missing id: {doc}"
        assert "name" in doc, f"Document missing name: {doc}"

        # Must have text or extracts
        has_text = "full_text" in doc and doc["full_text"]
        has_extracts = "extracts" in doc and doc["extracts"]
        assert has_text or has_extracts, f"Document has no text: {doc['id']}"

    print("Dataset validation passed!")
    return True
```

### Test Model Connection

```python
async def test_model_connection(model_name: str = "default"):
    """Test that model configuration is working."""

    from argumentation_analysis.evaluation.model_registry import ModelRegistry
    from openai import AsyncOpenAI
    import os

    registry = ModelRegistry.from_env()
    saved = registry.save_env()

    try:
        registry.activate(model_name)

        client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )

        response = await client.chat.completions.create(
            model=os.environ.get("OPENAI_CHAT_MODEL_ID"),
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )

        print(f"Model {model_name} is working!")
        print(f"Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"Model {model_name} failed: {e}")
        return False
    finally:
        registry.restore_env(saved)
```

### Benchmark Health Check

```python
async def health_check():
    """Run a quick health check on all components."""

    print("Testing evaluation framework...")

    # 1. Test dataset loading
    try:
        runner = BenchmarkRunner(ModelRegistry.from_env())
        runner.load_dataset_unencrypted("corpus.json")
        print(f"✓ Dataset loaded: {len(runner.dataset)} documents")
    except Exception as e:
        print(f"✗ Dataset failed: {e}")
        return

    # 2. Test model connection
    try:
        result = await runner.run_cell(
            workflow_name="light",
            model_name="default",
            document_index=0,
            timeout=30.0,
        )
        if result.success:
            print(f"✓ Model connection OK")
        else:
            print(f"✗ Model failed: {result.error}")
    except Exception as e:
        print(f"✗ Model connection failed: {e}")
        return

    # 3. Test result collection
    try:
        collector = ResultCollector()
        collector.save(result)
        print(f"✓ Result collection OK")
    except Exception as e:
        print(f"✗ Result collection failed: {e}")

    print("\nHealth check complete!")
```

---

## Configuration File

### `evaluation_config.yaml`

Create a configuration file for reproducible benchmarks:

```yaml
# Evaluation Configuration

models:
  default:
    model_id: "gpt-5-mini"
    base_url: "https://api.openai.com/v1"
    api_key_env_var: "OPENAI_API_KEY"
    display_name: "GPT-5 Mini"
    cost_per_1k_tokens: 0.0001

  gpt4:
    model_id: "gpt-4-turbo"
    base_url: "https://api.openai.com/v1"
    api_key_env_var: "OPENAI_API_KEY"
    display_name: "GPT-4 Turbo"
    cost_per_1k_tokens: 0.01

workflows:
  - name: "light"
    phases: ["extract", "quality", "counter"]
  - name: "standard"
    phases: ["extract", "quality", "counter", "jtms", "governance", "debate"]

datasets:
  baseline:
    path: "argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json"
    encrypted: false

  custom:
    path: "custom_corpus.json"
    encrypted: true
    passphrase: "your-passphrase"

settings:
  timeout: 120.0
  max_text_chars: 5000
  results_dir: "argumentation_analysis/evaluation/results"
  log_level: "INFO"
```

### Loading Configuration

```python
import yaml

def load_evaluation_config(config_path: str):
    """Load evaluation configuration from YAML file."""

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Create model registry
    registry = ModelRegistry.from_env()
    for name, model_config in config["models"].items():
        if name != "default":
            registry.register(name, ModelConfig(**model_config))

    # Load datasets
    runner = BenchmarkRunner(registry)
    for name, dataset_config in config["datasets"].items():
        if dataset_config["encrypted"]:
            runner.load_dataset_encrypted(
                dataset_config["path"],
                dataset_config["passphrase"]
            )
        else:
            runner.load_dataset_unencrypted(dataset_config["path"])

    # Apply settings
    settings = config["settings"]
    os.environ["EVALUATION_TIMEOUT"] = str(settings["timeout"])
    os.environ["EVALUATION_MAX_TEXT_CHARS"] = str(settings["max_text_chars"])

    logging.getLogger().setLevel(getattr(logging, settings["log_level"]))

    return registry, runner, config
```
