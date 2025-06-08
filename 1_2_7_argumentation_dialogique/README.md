# Dialogical Argumentation System

A sophisticated multi-agent debate system where AI agents with different personalities argue about various topics using structured argumentation and GPT API.

## Features

- **Multiple Agent Personalities**: 6 different agent types with unique argumentation styles
- **Structured Debates**: Organized arguments with claims, evidence, and rebuttals
- **Real-time Scoring**: Automatic evaluation of argument strength and quality
- **Debate Recording**: Saves complete debate transcripts to JSON files
- **Interactive Interface**: Command-line interface for easy use

## Agent Personalities

1. **The Scholar**: Academic and evidence-based, relies on research and studies
2. **The Pragmatist**: Focuses on practical implications and real-world consequences
3. **The Devil's Advocate**: Challenges assumptions and points out flaws in reasoning
4. **The Idealist**: Argues from principles and moral foundations
5. **The Skeptic**: Questions everything and demands strong evidence
6. **The Populist**: Represents common sense and popular opinion

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

## Usage

### Interactive Mode
```bash
python argumentation_main.py
```

### Command Line Mode
```bash
python argumentation_main.py "Should artificial intelligence be regulated by governments?"
```

### Example Topics
- "Should social media platforms be regulated more strictly?"
- "Is remote work better than office work?"
- "Should universities be free for everyone?"
- "Is artificial intelligence a threat to humanity?"
- "Should we prioritize economic growth over environmental protection?"

## Output

The system will:
1. Display the debate topic and participants
2. Show each argument with strength scores
3. Declare a winner based on argument quality
4. Save the complete debate to a timestamped JSON file

## Example Output

```
🎭 Starting debate on: Should artificial intelligence be regulated by governments?
📋 Participants: The Scholar (for), The Skeptic (against)
================================================================================

🗣️  Turn 1: The Scholar (for)
📝 Governments must regulate AI to prevent potential harms to society. Research from Oxford and MIT demonstrates that unregulated AI development could lead to job displacement, privacy violations, and algorithmic bias. The European Union's AI Act provides a framework for responsible AI governance while still allowing innovation.
💪 Strength: 0.75

🗣️  Turn 2: The Skeptic (against)
📝 Government regulation of AI is premature and potentially harmful. We lack sufficient understanding of AI's long-term implications to create effective policies. Heavy-handed regulation could stifle innovation and push development to less regulated jurisdictions, ultimately making us less competitive globally.
💪 Strength: 0.65

...
```

## Architecture

- **ArgumentationAgent**: Base class for AI agents with different personalities
- **DebateModerator**: Manages debate flow, rules, and scoring
- **ArgumentationSystem**: Main orchestrator that creates agents and runs debates
- **Argument**: Data structure representing individual arguments
- **DebateState**: Tracks the complete state of an ongoing debate

## Customization

You can easily:
- Add new agent personalities by modifying the `agent_personalities` dictionary
- Adjust debate rules in the `DebateModerator` class
- Modify argument scoring algorithms
- Change the GPT model or parameters in the `_call_gpt` method

## Requirements

- Python 3.7+
- OpenAI API key
- Internet connection for API calls
