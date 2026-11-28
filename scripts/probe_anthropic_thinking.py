"""Probe thinking modes on Anthropic's OpenAI-compatible endpoint (#3658).

Successful requests are billable. Nothing is sent without --confirm-spend.
"""

import argparse
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--confirm-spend", action="store_true")
    args = parser.parse_args()
    if not args.confirm_spend:
        parser.error("successful calls cost money; pass --confirm-spend to proceed")
    from openai import OpenAI, APIStatusError

    client = OpenAI(api_key=os.environ["ANTHROPIC_API_KEY"], base_url="https://api.anthropic.com/v1", max_retries=0)
    for mode in ("disabled", "enabled", "between_tools", "adaptive", "auto"):
        thinking = {"type": mode}
        if mode == "enabled":
            thinking["budget_tokens"] = 1024
        try:
            client.chat.completions.create(model=args.model, messages=[{"role": "user", "content": "Reply OK."}], max_tokens=1100, extra_body={"thinking": thinking})
        except APIStatusError as exc:
            print(f"{mode}: HTTP {exc.status_code}")
        else:
            print(f"{mode}: accepted (billable)")


if __name__ == "__main__":
    main()
