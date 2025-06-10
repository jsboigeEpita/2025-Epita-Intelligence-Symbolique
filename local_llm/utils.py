"""
This file contains utilitary functions.
"""

import re
import json

LEGACY_PROMPT = """
You are a specialist in fallacies.
Your task is to:
1. Identify the main arguments in the input.
2. Say if the arguments are valid and explain why.

Rules:
- ONLY analyze the input.
- DO NOT invent content or arguments.
- If there are no arguments, say so.
- Go straight to the point.
- End your answer with <END>

Input (between <input> and </input>):

<input>
***prompt***
</input>

Your analysis (end your answer with <END>):
"""


def get_full_prompt(prompt: str) -> str:
    """
    Constructs a full prompt for a fallacy analysis task.

    The returned prompt instructs a language model to:
    1. Identify arguments in the input.
    2. Determine whether each argument is valid or fallacious.
    3. Name and explain any detected fallacies.
    4. Return the output in a specific JSON format, ending with <END>.

    Args:
        prompt (str): The input text containing potential arguments.

    Returns:
        str: A formatted multi-line instruction prompt embedding the input.
    """

    full_prompt = f"""
You are a specialist in fallacies.
Your task is to:
1. Identify the main arguments in the input.
2. Say if each argument is valid or contains a fallacy.
3. If it contains a fallacy, name the fallacy and explain why.

Rules:
- ONLY analyze the input.
- DO NOT invent content or arguments.
- If there are no arguments, return an empty list for arguments.
- Be concise and factual.
- Format your answer in JSON as shown below.
- End your response with <END> on a new line.

Output format (must be a valid JSON):
{{
  "arguments": [
    {{
      "text": "The argument as found in the input.",
      "is_valid": true/false,
      "fallacy_type": "Name of the fallacy or null if valid.",
      "explanation": "Short explanation."
    }},
    ...
  ]
}}

Input (between <input> and </input>):

<input>
{prompt}
</input>

Your analysis (in JSON, end with <END>):
"""

    return full_prompt.strip()


def clean_output(output: str) -> str:
    """
    Cleans the model's output by removing everything after an end marker.

    Searches for known end tags (e.g., <END>, (END), END) and truncates the output
    at the first occurrence of any of them. If no end marker is found, returns the full
    output prefixed with a warning message.

    Args:
        output (str): The raw output string to clean.

    Returns:
        str: The cleaned output string, or the original output with a warning if no end tag.
    """
    for ending_tag in ["<END>", "(END)", "</END>", "</END/>", "END"]:
        index = output.find(ending_tag)
        if index != -1:
            return output[:index]
    return "No end of output found, here is the full output:\n\n" + output


def extract_json_from_string(input_string):
    """
    Extracts the first JSON object found within a given string.

    The function searches for a substring that resembles a JSON object (enclosed
    in curly braces `{}`), attempts to parse it, and returns it as a Python dictionary.

    Args:
        input_string (str): The string containing text and a JSON object.

    Returns:
        dict or None: The parsed JSON object as a dictionary if found and valid,
                      otherwise None.
    """
    pattern = r"(\{(?:.|\n)*\})"
    match = re.search(pattern, input_string)

    if match:
        json_string = match.group(1)

        try:
            json_obj = json.loads(json_string)
            return json_obj
        except json.JSONDecodeError:
            print("Error decoding JSON.")
            return None
    else:
        print("No JSON object found.")
        return None
