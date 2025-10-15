import openai
import os
from dotenv import load_dotenv

load_dotenv()
# Fix: Set the API key explicitly if not set in the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Optionally, you can hardcode your key here for testing (not recommended for production)
    # OPENAI_API_KEY = "sk-..."
    raise RuntimeError(
        "OPENAI_API_KEY environment variable is not set. Please set it before running."
    )

openai.api_key = OPENAI_API_KEY


def gpt_llm_fn(input_text: str) -> str:
    """
    Calls OpenAI GPT (>=1.0.0) to get a score between 0 and 1.
    """
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # or "gpt-4"
        messages=[
            {
                "role": "system",
                "content": "Réponds uniquement par un score numérique entre 0 et 1, sans explication.",
            },
            {"role": "user", "content": input_text},
        ],
        max_tokens=10,
        temperature=0.0,
        n=1,
    )
    score = response.choices[0].message.content.strip()
    return score
