def get_full_prompt(prompt: str) -> str:
    full_prompt = f"""
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
{prompt}
</input>

Your analysis (end your answer with <END>):
"""
    return full_prompt.strip()

def clean_output(output: str) -> str:
    for ending_tag in ["<END>"]:
        index = output.upper().find(ending_tag)
        if (index != -1):
            return output[:index]
    return  "No end of output found, here is the full output:\n\n" + output
