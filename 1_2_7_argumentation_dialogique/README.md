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
python enhanced_argumentation_main.py
```

### Command Line Mode
```bash
python enhanced_argumentation_main.py "Should artificial intelligence be regulated by governments?"
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
🎭 ENHANCED DEBATE SYSTEM
📋 Topic: Is Pasta better then Rice ?
👥 Participants: The Populist (for), The Economist (against)
================================================================================

🎬 OPENING PHASE
----------------------------------------

🗣️  Turn 1: The Populist (for) - opening_statement
2025-06-27 10:49:43,074 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
📝 Ladies and gentlemen, esteemed opponents, and fellow debaters, today we gather to delve into the age-old question: Is pasta better than rice? As The Populist, I stand firmly on the side of pasta, not just as a matter of personal preference but based on solid reasoning and widespread popularity.

Pasta is a versatile culinary delight that caters to a multitude of tastes and preferences. Whether it's comforting spaghetti bolognese, creamy fettuccine alfredo, or zesty penne arrabbiata, pasta offers a diverse range of flavors and textures that can satisfy anyone's palate. Additionally, pasta dishes are often quick and easy to prepare, making them a convenient choice for busy individuals and families.

Furthermore, pasta has been a staple in many cultures for centuries, transcending borders and becoming a beloved dish worldwide. Its enduring popularity speaks volumes about its appeal and adaptability to different culinary traditions.

In light of recent arguments, I acknowledge that rice also holds its own place in the hearts and kitchens of many. However, when considering factors such as versatility, flavor, and global appeal, pasta emerges as the superior choice for a satisfying and enjoyable dining experience. Join me in celebrating the magnificence of pasta as we embark on this flavorful debate journey.
📊 Analysis:
   • Persuasiveness: 0.48
   • Evidence Quality: 0.30
   • Logic Score: 0.50
   • Readability: 0.29
👏 Audience Impact: +4 points
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
