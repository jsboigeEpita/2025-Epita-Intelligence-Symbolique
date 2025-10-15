"""
Rule patterns for Argument Mining in French.

These patterns are designed to help identify claims and premises using spaCy's Matcher.
They are basic examples and can be extended for more complex linguistic structures.
"""

# Patterns for identifying Claims
# Claims often express a main point, conclusion, or assertion.
claim_patterns = [
    # Pattern 1: "Je pense que...", "Nous croyons que..."
    {
        "PATTERN": [
            {"LOWER": {"IN": ["je", "nous"]}},
            {"LEMMA": {"IN": ["penser", "croire", "affirmer"]}},
            {"LOWER": "que"},
            {"OP": "+"},
        ]
    },
    # Pattern 2: Phrases indicating a conclusion: "Donc...", "Par conséquent...", "En conclusion..."
    {
        "PATTERN": [
            {"LOWER": {"IN": ["donc", "par", "en"]}},
            {"LOWER": {"IN": ["conséquent", "conclusion"]}},
            {"IS_PUNCT": True, "OP": "?"},
            {"OP": "+"},
        ]
    },
    # Pattern 3: Assertive statements (simple declarative sentences, often without explicit markers)
    # This is harder to capture with simple rules and often requires more advanced NLP.
    # For now, we'll focus on explicit markers.
]

# Patterns for identifying Premises
# Premises often provide reasons, evidence, or support for a claim.
premise_patterns = [
    # Pattern 1: "Parce que...", "Car...", "Étant donné que..."
    {
        "PATTERN": [
            {"LOWER": {"IN": ["parce", "car", "étant"]}},
            {"LOWER": {"IN": ["que", "donné"]}},
            {"OP": "+"},
        ]
    },
    # Pattern 2: "Selon [source]...", "D'après [source]..."
    {
        "PATTERN": [
            {"LOWER": {"IN": ["selon", "d'après"]}},
            {"POS": "NOUN"},
            {"OP": "+"},
        ]
    },
    # Pattern 3: "Les faits montrent que...", "Des études indiquent que..."
    {
        "PATTERN": [
            {"LOWER": {"IN": ["les", "des"]}},
            {"POS": "NOUN"},
            {"LEMMA": {"IN": ["montrer", "indiquer"]}},
            {"LOWER": "que"},
            {"OP": "+"},
        ]
    },
]
