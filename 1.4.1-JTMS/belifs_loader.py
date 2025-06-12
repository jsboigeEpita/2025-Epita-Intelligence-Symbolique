import json
import os

def load_beliefs(filename, jtms):
    print(os.path.abspath("."))
    with open(f"Beliefs/{filename}", 'r') as f:
        data = json.load(f)

    for b in data["beliefs"]:
        jtms.add_justification(b["in"], b["out"], b["conclusion"])
    
    for init in data.get("initial", []):
        jtms.add_belief(init)
        jtms.beliefs[init].valid = True

    return jtms