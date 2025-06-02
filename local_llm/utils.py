# This file contains utilitary functions
# used by the local_llm package.

legacy_prompt = f"""
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

Output format (JSON):
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
    for ending_tag in ["<END>", "(END)", "</END>", "</END/>", "END"]:
        index = output.find(ending_tag)
        if (index != -1):
            return output[:index]
    return  "No end of output found, here is the full output:\n\n" + output
