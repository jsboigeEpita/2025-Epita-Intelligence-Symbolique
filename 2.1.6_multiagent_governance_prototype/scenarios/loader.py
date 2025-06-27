import os
import json

def load_scenario(path):
    with open(path) as f:
        return json.load(f)

def list_scenarios():
    return [f for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.json')] 