# Technical Design: Parallel Exploration Workflow for Fallacy Detection

## 1. Overview

This document outlines the technical design for a parallel exploration workflow for the fallacy detection agent. The goal is to enable the agent to launch approximately ten independent explorations of a taxonomy tree simultaneously and synthesize the results into a coherent analysis. This new workflow will be integrated with the `semantic-kernel` library, leveraging its asynchronous capabilities to manage parallel calls to language models efficiently.

## 2. Architecture

This section describes the overall architecture of the parallel workflow system. The design is centered around a new orchestrator component, the `ParallelWorkflowManager`, which leverages `semantic-kernel` for its core AI functionalities.

### 2.1. Architecture Diagram

```mermaid
graph TD
    A[User Request: Analyze Text] --> B{ParallelWorkflowManager};
    
    subgraph "Orchestration"
        B -- 1. Distributes tasks --> C1[Exploration Task 1\n(Fallacy Branch A)];
        B -- 1. Distributes tasks --> C2[Exploration Task 2\n(Fallacy Branch B)];
        B -- 1. Distributes tasks --> C3[...];
        B -- 1. Distributes tasks --> C10[Exploration Task 10\n(Fallacy Branch J)];
    end

    subgraph "Semantic Kernel - Parallel Execution (asyncio)"
        C1 -- 2. Invokes Kernel --> K1[Kernel Function: DetectFallacy];
        C2 -- 2. Invokes Kernel --> K2[Kernel Function: DetectFallacy];
        C3 -- 2. Invokes Kernel --> K3[...];
        C10 -- 2. Invokes Kernel --> K10[Kernel Function: DetectFallacy];
    end

    K1 -- 3. Returns a structured result --> D{Result Aggregator};
    K2 -- 3. Returns a structured result --> D;
    K3 -- 3. Returns a structured result --> D;
    K10 -- 3. Returns a structured result --> D;

    D -- 4. Provides consolidated data --> E[Synthesis Plugin: SynthesizeResults];
    E -- 5. Invokes Kernel for Synthesis --> F[Final Coherent Response];
    
    B --> D;
    B --> E;

```

### 2.2. Component Descriptions

- **User Request:** The initial input containing the raw text to be analyzed for logical fallacies.

- **ParallelWorkflowManager:** A new, high-level Python class responsible for orchestrating the entire parallel workflow. It initializes the `semantic-kernel`, loads the necessary plugins, and manages the execution flow. Its primary role is to divide the exploration work, dispatch the tasks, and trigger the final synthesis.

- **Exploration Task:** A logical, in-memory task created and managed by the `ParallelWorkflowManager`. Each task represents an independent exploration of a specific branch of the fallacy taxonomy. It is an asynchronous function call that invokes a dedicated `semantic-kernel` function (`DetectFallacy`), passing the user's text and the specific fallacy branch as arguments.

- **Result Aggregator:** A component within the `ParallelWorkflowManager` that collects and synchronizes the structured results (e.g., JSON objects) from all concurrently running `Exploration Task` instances. It uses a mechanism like `asyncio.gather` to wait for all tasks to complete before consolidation.

- **Synthesis Plugin:** A dedicated `semantic-kernel` plugin (`SynthesisPlugin`) containing a function (`SynthesizeResults`). This function is designed to take the aggregated, multi-faceted results from the aggregator and produce a single, human-readable, and coherent analysis. It leverages the LLM's summarization and reasoning capabilities to merge different findings.

- **Final Response:** The structured, synthesized output delivered to the end-user, detailing the detected fallacies, confidence levels, and supporting evidence from the text.

## 3. Data Flow

1.  **Initiation:** A user submits a text for analysis. The `ParallelWorkflowManager` is instantiated with a `semantic-kernel` instance.
2.  **Dispatch:** The manager's entry point method (e.g., `execute_parallel_workflow`) is called. It defines a list of fallacy taxonomy paths to be explored. It then creates N asynchronous `Exploration Task` coroutines, one for each path.
3.  **Parallel Execution (asyncio):** The `ParallelWorkflowManager` uses `asyncio.gather` to run all `Exploration Task` coroutines concurrently. Each task internally calls the `kernel.invoke()` method, which triggers an asynchronous API call to the configured language model.
4.  **Result Collection:** As each LLM API call completes, the `semantic-kernel` function returns a structured result (e.g., a Pydantic or dictionary object) for its specific taxonomy branch. `asyncio.gather` collects these results into a list.
5.  **Aggregation & Synchronization:** Once all tasks are complete, the `Result Aggregator` (a part of the manager's logic) holds a list of all individual findings. This list is the consolidated dataset.
6.  **Synthesis:** The aggregated list of findings is passed as input to the `SynthesisPlugin.SynthesizeResults` function via another `kernel.invoke()` call.
7.  **Final Output:** The synthesis plugin returns the final, comprehensive report, which is then delivered to the user.

## 4. Parallelism Model Analysis

### 4.1. asyncio

-   **Description:** An asynchronous programming model in Python that uses an event loop to manage a set of coroutines. It is designed for I/O-bound and high-level structured network code.
-   **Pros:**
    -   **Efficiency for I/O-Bound Tasks:** The primary bottleneck in our workflow is network latency from making ~10 simultaneous API calls to a language model. `asyncio` excels at this by allowing the program to perform other work while waiting for responses.
    -   **Native `semantic-kernel` Support:** The `semantic-kernel` library is designed with a robust async-first approach, making integration seamless.
    -   **Lower Overhead:** Compared to multi-threading, `asyncio` generally has lower memory and context-switching overhead.
-   **Cons:**
    -   **No True CPU Parallelism:** `asyncio` runs on a single CPU core and does not circumvent Python's Global Interpreter Lock (GIL). This is not a significant drawback for our use case, as the tasks are I/O-bound, not CPU-bound.

### 4.2. Multi-threading

-   **Description:** A model where the operating system manages multiple threads of execution within a single process.
-   **Pros:**
    -   Can be conceptually simpler for developers new to asynchronous programming.
-   **Cons:**
    -   **Global Interpreter Lock (GIL):** The GIL prevents multiple threads from executing Python bytecode simultaneously, nullifying the benefits for CPU-bound tasks and adding overhead for I/O-bound tasks due to context switching.
    -   **Complexity:** Requires careful management of shared resources and thread synchronization (locks, queues), which can lead to race conditions and deadlocks.
    -   **Less Synergistic with `semantic-kernel`:** While possible to integrate, it doesn't align as cleanly with the library's native async architecture.

### 4.3. Recommendation

The recommended and superior approach is **asyncio**. It is the most performant and idiomatic solution for this specific problem, as the workflow is dominated by I/O-bound operations (LLM API calls). Its native integration with `semantic-kernel` ensures a clean, efficient, and scalable implementation.

## 5. Proposed API Definitions

### 5.1. ParallelWorkflowManager Implementation Sketch

```python
import asyncio
from semantic_kernel import Kernel

class ParallelWorkflowManager:
    """
    Orchestrates a parallel fallacy detection workflow using semantic-kernel.
    """

    def __init__(self, kernel: Kernel):
        """
        Initializes the manager with a semantic-kernel instance.

        :param kernel: An initialized semantic-kernel object.
        """
        self.kernel = kernel
        # Assume the kernel has fallacy detection and synthesis plugins loaded
        self.fallacy_detection_func = self.kernel.plugins["FallacyDetectionPlugin"]["DetectFallacy"]
        self.synthesis_func = self.kernel.plugins["SynthesisPlugin"]["SynthesizeResults"]

    async def _run_single_exploration(self, text: str, taxonomy_path: str) -> dict:
        """
        Runs a single exploration task for a given taxonomy path.

        :param text: The input text to analyze.
        :param taxonomy_path: The specific fallacy taxonomy branch to explore.
        :return: A dictionary containing the findings for this branch.
        """
        # The kernel function would be invoked with specific arguments
        result = await self.kernel.invoke(
            self.fallacy_detection_func,
            text=text,
            taxonomy_path=taxonomy_path
        )
        # It's assumed the kernel function returns a structured dictionary
        return result.value

    async def execute_parallel_workflow(self, text: str, taxonomy_paths: list[str]) -> dict:
        """
        Executes the full parallel exploration and synthesis workflow.

        :param text: The input text to analyze.
        :param taxonomy_paths: A list of taxonomy paths to explore in parallel.
        :return: A dictionary containing the final synthesized result.
        """
        # 1. Create all concurrent tasks
        exploration_tasks = [
            self._run_single_exploration(text, path) for path in taxonomy_paths
        ]

        # 2. Run tasks in parallel and collect results
        aggregated_results = await asyncio.gather(*exploration_tasks)

        # 3. Pass aggregated results to the synthesis plugin
        synthesis_result = await self.kernel.invoke(
            self.synthesis_func,
            input_findings=aggregated_results
        )

        return synthesis_result.value
```

### 5.2. Synthesis Plugin Prompt

A new plugin is required for the synthesis step.

**Directory Structure:**
```
/plugins/
└── SynthesisPlugin/
    └── SynthesizeResults/
        ├── skprompt.txt
        └── config.json
```

**`skprompt.txt` for `SynthesizeResults`:**
```
Synthesize the following list of findings from multiple, parallel fallacy detection agents into a single, comprehensive and well-structured report.
Each finding corresponds to the analysis of a different fallacy category.
Your task is to merge these independent analyses, resolve redundancies, and present a final, unified summary.

RULES:
- If a fallacy is identified by multiple agents, consolidate their findings, using the highest confidence score and summarizing the evidence.
- List each unique fallacy identified.
- For each fallacy, provide a clear definition, the consolidated confidence score (from 0.0 to 1.0), and a concise summary of the textual evidence.
- If no fallacies are found, state that clearly.

Input Findings (JSON list):
{{$input_findings}}

---
Synthesized Fallacy Report:
```

**`config.json` for `SynthesizeResults`:**
```json
{
  "schema": 1,
  "type": "completion",
  "description": "Synthesizes findings from multiple parallel agents into one report.",
  "completion": {
    "temperature": 0.2,
    "max_tokens": 1500
  },
  "input_variables": [
    {
      "name": "input_findings",
      "description": "A JSON string representing a list of findings from the parallel exploration tasks.",
      "required": true
    }
  ]
}