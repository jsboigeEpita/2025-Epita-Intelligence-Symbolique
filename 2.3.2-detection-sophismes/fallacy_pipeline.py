

"""
Main file for the French Fallacy Detection Pipeline.
This file outlines the structure and flow of the system.
"""

from typing import List, Dict, Any
import torch
from transformers import CamembertForSequenceClassification, CamembertTokenizer
import json
import pandas as pd
import spacy
from spacy.matcher import Matcher
from symbolic_rules import fallacy_rules
from argument_mining_rules import claim_patterns, premise_patterns

# Load metadata for the neural model
with open('./data/french_metadata.json', 'r') as f:
    metadata = json.load(f)
num_labels = metadata['num_classes']
id_to_label = {v: k for k, v in metadata['reverse_label_mapping'].items()}

# Standardize fallacy names for ensembling
fallacy_name_mapping = {
    "ad hominem": "Attaque personnelle (Ad Hominem)",
    "ad populum": "Appel à la popularité (Ad Populum)",
    "appel à l'émotion": "Appel à l'émotion (Appeal to Emotion)",
    "fallacy of credibility": "Fallacy de crédibilité",
    "fallacy of extension": "Fallacy d'extension",
    "fallacy of logic": "Fallacy de logique",
    "faulty generalization": "Généralisation hâtive (Hasty Generalization)",
    "fausse causalité": "Fausse causalité (False Cause)",
    "faux dilemme": "Faux dilemme (False Dilemma)",
    "intentional": "Intentionnel",
    "raisonnement circulaire": "Raisonnement circulaire (Circular Reasoning)",
    "sophisme de pertinence": "Sophisme de pertinence",
    "équivoque": "Équivoque (Equivocation)",
    "Argument d'autorité (Appeal to Authority)": "Argument d'autorité (Appeal to Authority)", # Already standardized
    "Attaque personnelle (Ad Hominem)": "Attaque personnelle (Ad Hominem)", # Already standardized
    "Généralisation hâtive (Hasty Generalization)": "Généralisation hâtive (Hasty Generalization)", # Already standardized
    "Appel à la tradition (Appeal to Tradition)": "Appel à la tradition (Appeal to Tradition)", # Already standardized
    "Pente glissante (Slippery Slope)": "Pente glissante (Slippery Slope)" # Already standardized
}

# Load pre-trained CamemBERT model and tokenizer
tokenizer = CamembertTokenizer.from_pretrained('./fine_tuned_camembert')
model = CamembertForSequenceClassification.from_pretrained('./fine_tuned_camembert', num_labels=num_labels)

nlp = spacy.load("fr_core_news_lg")

# --- Module 1: Argument Mining ---
def argument_mining_module(text: str) -> Dict[str, List[str]]:
    """
    Identifies claims and premises in the input text using spaCy and rule-based patterns.
    """
    print(f"1. Mining arguments from: '{text[:50]}...'")
    
    doc = nlp(text)
    
    claim_matcher = Matcher(nlp.vocab)
    for i, pattern in enumerate(claim_patterns):
        claim_matcher.add(f"CLAIM_PATTERN_{i}", [pattern["PATTERN"]])

    premise_matcher = Matcher(nlp.vocab)
    for i, pattern in enumerate(premise_patterns):
        premise_matcher.add(f"PREMISE_PATTERN_{i}", [pattern["PATTERN"]])

    claims = []
    premises = []

    for sent in doc.sents:
        sent_text = sent.text
        
        # Check for claims
        claim_matches = claim_matcher(sent)
        if claim_matches:
            claims.append(sent_text)
            continue # If it's a claim, it's less likely to be a premise in the same sentence

        # Check for premises
        premise_matches = premise_matcher(sent)
        if premise_matches:
            premises.append(sent_text)

    # Fallback: if no explicit claims/premises found, treat sentences as general arguments
    if not claims and not premises:
        # Simple heuristic: first sentence as claim, rest as premises
        if len(list(doc.sents)) > 0:
            claims.append(list(doc.sents)[0].text)
            premises.extend([s.text for s in list(doc.sents)[1:]])
        else:
            claims.append(text) # If only one sentence, treat whole text as claim

    return {"claims": claims, "premises": premises}

# --- Module 2: Neural Fallacy Classification ---
def neural_classification_module(arguments: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Performs multi-label fallacy classification using a transformer model.
    - Model: Fine-tuned CamemBERT, FlauBERT, or XLM-R.
    - Input: Claims and premises.
    - Output: List of potential fallacies with confidence scores.
    """
    print("2. Running neural classification...")
    
    # Combine claims and premises into a single text for classification
    input_text = " ".join(arguments['claims'] + arguments['premises'])
    
    # Tokenize the input text
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, padding=True)
    
    # Get model predictions
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Apply softmax to get probabilities for single-label classification
    probabilities = torch.softmax(outputs.logits, dim=1)
    
    # Get the predicted label (class with highest probability)
    predicted_class_id = torch.argmax(probabilities, dim=1).item()
    
    detected_fallacies = []
    fallacy_type = fallacy_name_mapping.get(id_to_label[predicted_class_id], id_to_label[predicted_class_id])
    confidence = probabilities[0][predicted_class_id].item()
    detected_fallacies.append({"fallacy_type": fallacy_type, "confidence": confidence})
            
    return detected_fallacies

# --- Module 3: Symbolic Pattern Matching ---
import spacy
from spacy.matcher import Matcher
from symbolic_rules import fallacy_rules

nlp = spacy.load("fr_core_news_lg")

def symbolic_matching_module(arguments: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Matches arguments against a predefined set of French fallacy rules.
    - Uses a rule-based engine (e.g., spaCy's Matcher or custom logic).
    """
    print("3. Running symbolic pattern matching...")
    
    matcher = Matcher(nlp.vocab)
    for fallacy_type, rules in fallacy_rules.items():
        for rule in rules:
            matcher.add(fallacy_type, [rule["PATTERN"]])
    
    doc = nlp(" ".join(arguments['claims'] + arguments['premises']))
    matches = matcher(doc)
    
    results = []
    for match_id, start, end in matches:
        rule_name = nlp.vocab.strings[match_id]
        span = doc[start:end]
        
        user_friendly_fallacy_type = rule_name
        if rule_name in fallacy_rules and len(fallacy_rules[rule_name]) > 0:
            user_friendly_fallacy_type = fallacy_rules[rule_name][0]["FALLACY_TYPE"]

        results.append({"fallacy_type": user_friendly_fallacy_type, "matched_rule": span.text, "confidence": 1.0})
        
    return results

# --- Module 4: Ensemble & Verification ---
def ensemble_and_verification_module(
    neural_results: List[Dict[str, Any]], 
    symbolic_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Combines results from neural and symbolic engines.
    - Can use a voting system, weighted scores, or a meta-classifier.
    - Optional: RAG for external evidence retrieval.
    """
    print("4. Ensembling and verifying results...")
    
    combined_fallacies = {}

    # Process neural results
    for res in neural_results:
        standardized_fallacy_type = fallacy_name_mapping.get(res['fallacy_type'], res['fallacy_type'])
        combined_fallacies[standardized_fallacy_type] = {
            "source": "neural",
            "confidence": res['confidence']
        }

    # Process symbolic results
    for res in symbolic_results:
        standardized_fallacy_type = fallacy_name_mapping.get(res['fallacy_type'], res['fallacy_type'])
        
        if standardized_fallacy_type in combined_fallacies:
            # Fallacy detected by both neural and symbolic
            # Combine confidence (e.g., average, or take max if symbolic is 1.0)
            # For now, if symbolic is 1.0, it overrides neural confidence
            if res['confidence'] == 1.0: # Symbolic detections are assumed to be high confidence
                combined_fallacies[standardized_fallacy_type]['confidence'] = 1.0
            else:
                # Simple average if both have confidence scores
                combined_fallacies[standardized_fallacy_type]['confidence'] = \
                    (combined_fallacies[standardized_fallacy_type]['confidence'] + res['confidence']) / 2
            
            combined_fallacies[standardized_fallacy_type]['source'] += "+symbolic"
            combined_fallacies[standardized_fallacy_type]['matched_rule'] = res['matched_rule']
        else:
            # Fallacy detected only by symbolic
            combined_fallacies[standardized_fallacy_type] = {
                "source": "symbolic",
                "confidence": res['confidence'], # Symbolic confidence is typically 1.0
                "matched_rule": res['matched_rule']
            }
            
    # Optional RAG step:
    # for fallacy, data in combined_fallacies.items():
    #     if needs_verification(fallacy):
    #         evidence = retrieve_evidence(arguments['claims'])
    #         data['verification'] = verify_with_evidence(evidence)
            
    return {"detected_fallacies": combined_fallacies}

# --- Module 5: Explanation Generation ---
def explanation_generation_module(
    original_text: str,
    arguments: Dict[str, List[str]],
    analysis_results: Dict[str, Any]
) -> str:
    """
    Generates a clear, natural-language explanation in French.
    - Uses a fine-tuned generative model (e.g., T5-base-french or GPT).
    """
    print("5. Generating explanation...")
    
    fallacies = analysis_results.get("detected_fallacies", {})
    if not fallacies:
        return "Aucune erreur de raisonnement détectée dans le texte fourni."

    explanation = f"""Analyse du texte : '{original_text}'

Composants argumentatifs identifiés :
- Affirmation(s) : {arguments['claims']}
- Prémisse(s) : {arguments['premises']}

Erreur(s) de raisonnement potentielle(s) détectée(s) :
"""

    for fallacy, data in fallacies.items():
        explanation += f"""- **Type d'erreur : {fallacy}**
  - Confiance : {data.get('confidence', 'N/A'):.2f}
  - Source de détection : {data.get('source', 'N/A')}
"""
        if 'matched_rule' in data:
            explanation += f"  - Règle symbolique : {data['matched_rule']}\n"
        
        # Template-based explanation for demonstration
        if fallacy == "Argument d'autorité (Appeal to Authority)":
            justification = "L'argument s'appuie sur l'opinion d'une figure d'autorité sans fournir de preuves suffisantes pour étayer l'affirmation."
        elif fallacy == "Généralisation hâtive (Hasty Generalization)":
            justification = "Une conclusion générale est tirée à partir d'un échantillon trop limité ou non représentatif."
        elif fallacy == "Attaque personnelle (Ad Hominem)":
            justification = "L'argument attaque la personne ou le caractère de l'adversaire plutôt que de réfuter son argument."
        elif fallacy == "fallacy of credibility":
            justification = "L'argument tente de discréditer une source ou une affirmation sans aborder le fond de l'argument."
        else:
            justification = f"Ce type d'erreur de raisonnement est détecté lorsque l'argument présente des caractéristiques de '{fallacy}'."

        explanation += f"  - Justification : {justification}\n"

    return explanation

# --- Main Pipeline Orchestrator ---
def run_fallacy_pipeline(text: str):
    """
    Orchestrates the full fallacy detection and explanation pipeline.
    """
    # 1. Argument Mining
    arguments = argument_mining_module(text)
    
    # 2. Parallel Fallacy Detection
    neural_results = neural_classification_module(arguments)
    symbolic_results = symbolic_matching_module(arguments)
    
    # 3. Ensemble & Verification
    analysis = ensemble_and_verification_module(neural_results, symbolic_results)
    
    # 4. Explanation Generation
    final_explanation = explanation_generation_module(text, arguments, analysis)
    
    print("\n" + "="*50)
    print("Rapport d'analyse final :")
    print("="*50)
    print(final_explanation)


if __name__ == '__main__':
    # Example usage with a sample text
    sample_text = "Un expert a dit à la télévision que l'IA est la plus grande menace pour l'humanité, donc ça doit être vrai. On ne peut pas faire confiance aux politiciens."
    run_fallacy_pipeline(sample_text)
