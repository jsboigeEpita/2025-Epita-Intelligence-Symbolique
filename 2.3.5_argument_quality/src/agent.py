# Agent d'Évaluation de la Qualité Argumentative
import json

import spacy
from typing import Dict, List
from textstat import flesch_reading_ease
import re

try:
    nlp = spacy.load("fr_core_news_sm")
except OSError:
    import subprocess

    subprocess.run(["python", "-m", "spacy", "download", "fr_core_news_sm"])
    nlp = spacy.load("fr_core_news_sm")

# Taxonomie étendue avec 9 vertus
VERTUES = [
    "clarte",
    "pertinence",
    "presence_sources",
    "refutation_constructive",
    "structure_logique",
    "analogie_pertinente",
    "fiabilite_sources",
    "exhaustivite",
    "redondance_faible",
]

with open("ressources_argumentatives.json", encoding="utf-8") as f:
    RESSOURCES_ARGUMENTATIVES = json.load(f)


class ArgumentEvaluationReport:
    def __init__(self, text: str):
        self.text = text
        self.scores = {}
        self.details = {}

    def to_dict(self):
        note_finale = sum(self.scores.values())
        return {
            "note_finale": note_finale,
            "note_moyenne": note_finale / len(self.scores) if self.scores else 0.0,
            "scores_par_vertu": self.scores,
            "rapport_detaille": self.details,
        }


# Détecteur de clarté : basé sur la lisibilité


def detect_clarte(text: str) -> (float, str):
    score = flesch_reading_ease(text)
    commentaire = f"Lisibilité (Flesch) : {score:.2f}. "
    if score >= 60:
        note = 1.0
        commentaire += "Texte clair."
    elif score >= 30:
        note = 0.5
        commentaire += "Texte moyennement clair."
    else:
        note = 0.2
        commentaire += "Texte difficile à comprendre."
    return note, commentaire


# Détecteur de pertinence : heuristique simple


def detect_pertinence(text: str) -> (float, str):
    doc = nlp(text)
    connecteurs = RESSOURCES_ARGUMENTATIVES["connecteurs_pertinence"]
    count = sum(1 for token in doc if token.text.lower() in connecteurs)
    if count >= 3:
        return 1.0, f"Connecteurs logiques détectés ({count}). Argument bien structuré."
    elif count >= 1:
        return (
            0.5,
            f"Quelques connecteurs logiques détectés ({count}). Structure partielle.",
        )
    else:
        return 0.2, "Peu ou pas de connecteurs logiques détectés. Structure faible."


# Détecteur de sources


def detect_presence_sources(text: str) -> (float, str):
    citation_patterns = RESSOURCES_ARGUMENTATIVES["citation_patterns"]
    count = 0
    for pattern in citation_patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    if count >= 2:
        return 1.0, f"{count} sources détectées."
    elif count == 1:
        return 0.5, "Une source détectée."
    else:
        return 0.0, "Aucune source détectée."


# Réfutation constructive


def detect_refutation_constructive(text: str) -> (float, str):
    marqueurs = RESSOURCES_ARGUMENTATIVES["marqueurs_refutation"]
    found = [m for m in marqueurs if m in text.lower()]
    if len(found) >= 1:
        return 1.0, f"Réfutation détectée avec les marqueurs : {found}."
    return 0.0, "Aucune réfutation constructive détectée."


# Bonne structure logique (simplifié)


def detect_structure_logique(text: str) -> (float, str):
    connecteurs = RESSOURCES_ARGUMENTATIVES["connecteurs_structure_logique"]
    found = [c for c in connecteurs if c in text.lower()]
    if len(found) >= 2:
        return 1.0, f"Structure logique détectée avec {len(found)} connecteurs."
    elif len(found) == 1:
        return 0.5, "Structure partiellement logique."
    return 0.0, "Structure logique faible."


# Analogies pertinentes


def detect_analogie_pertinente(text: str) -> (float, str):
    patterns = RESSOURCES_ARGUMENTATIVES["patterns_analogies"]
    found = [p for p in patterns if p in text.lower()]
    if len(found) >= 1:
        return 1.0, f"Analogie détectée : {found}."
    return 0.0, "Aucune analogie détectée."


# Fiabilité des sources (très simplifié)


def detect_fiabilite_sources(text: str) -> (float, str):
    credible_sources = RESSOURCES_ARGUMENTATIVES["credible_sources"]
    found = [src for src in credible_sources if src.lower() in text.lower()]
    if found:
        return 1.0, f"Sources crédibles détectées : {found}."
    return 0.0, "Pas de source crédible identifiable."


# Exhaustivité raisonnable (heuristique basée sur la longueur)


def detect_exhaustivite(text: str) -> (float, str):
    sentences = list(nlp(text).sents)
    if len(sentences) >= 5:
        return 1.0, f"{len(sentences)} phrases détectées. Couverture raisonnable."
    elif len(sentences) >= 3:
        return 0.5, "Couverture partielle du sujet."
    return 0.0, "Texte trop court pour juger de l’exhaustivité."


# Redondance faible (heuristique simple sur répétitions de mots)


def detect_redondance_faible(text: str) -> (float, str):
    words = [t.text.lower() for t in nlp(text) if t.is_alpha]
    unique = set(words)
    ratio = len(unique) / len(words) if words else 0
    if ratio > 0.7:
        return 1.0, "Peu de redondance détectée."
    elif ratio > 0.5:
        return 0.5, "Redondance modérée."
    return 0.0, "Forte redondance lexicale."


# Fonction principale


def evaluer_argument(text: str) -> Dict:
    report = ArgumentEvaluationReport(text)

    detecteurs = {
        "clarte": detect_clarte,
        "pertinence": detect_pertinence,
        "presence_sources": detect_presence_sources,
        "refutation_constructive": detect_refutation_constructive,
        "structure_logique": detect_structure_logique,
        "analogie_pertinente": detect_analogie_pertinente,
        "fiabilite_sources": detect_fiabilite_sources,
        "exhaustivite": detect_exhaustivite,
        "redondance_faible": detect_redondance_faible,
    }

    for vertu, fonction in detecteurs.items():
        note, commentaire = fonction(text)
        report.scores[vertu] = note
        report.details[vertu] = commentaire

    return report.to_dict()


ARGUMENTS_EXAMPLE = [
    # 0
    "Selon Smith (2020), les énergies renouvelables sont essentielles car elles réduisent les émissions. Cependant, leur mise en œuvre demande des investissements.",
    # 1 Clair, pertinent, avec source
    "Selon Dupont (2019), la réduction du temps de travail augmente la productivité car elle améliore le bien-être des employés.",
    # 2 Structure logique claire
    "Les abeilles sont essentielles à la pollinisation. Sans elles, la production alimentaire chuterait drastiquement.",
    # 3 Exemples concrets et pertinents
    "Le télétravail réduit les déplacements quotidiens, donc limite les émissions de CO₂.",
    # 4 Utilisation d’un raisonnement causal
    "Puisque l’eau bout à 100°C à pression atmosphérique, elle est idéale pour la stérilisation.",
    # 5 Référence explicite et connecteurs
    "Comme l’a montré l’étude de Martin (2022), une alimentation végétarienne réduit le risque cardiovasculaire.",
    # 6 Trop vague, sans lien clair
    "Manger des légumes est bon. C’est pourquoi les voitures polluent.",
    # 7 Pas de source, clarté faible
    "Il est dit que ça marche mieux comme ça pour les gens, donc voilà.",
    # 8 Sophisme de corrélation → causalité
    "Depuis que les gens boivent plus de café, les accidents de voiture ont diminué. Le café rend donc les routes plus sûres.",
    # 9 Pas de connecteurs logiques
    "Il faut plus de lois. Les gens font ce qu’ils veulent. Les choses vont mal.",
    # 10 Phrase trop complexe, style lourd
    "En vertu de l’impossibilité manifeste de contenir l’expansion exponentielle des données numériques, la législation, bien que présente, peine à s’appliquer dans un monde où l’information circule à la vitesse de la lumière.",
    # 11
    "Selon l'OMS, les campagnes de vaccination sont essentielles. Certains pensent que ces campagnes restreignent les libertés, mais cela est compensé par les bénéfices collectifs. À l’instar d’un bouclier, elles protègent indirectement les plus vulnérables.",
    # 12 Argument parfait
    "Selon un rapport de l'Agence Internationale de l'Énergie (2023), les énergies renouvelables sont cruciales pour lutter contre le changement climatique, car elles réduisent les émissions de CO2. Par exemple, remplacer les centrales à charbon par des parcs solaires permettrait de diminuer drastiquement la pollution, tout comme remplacer une vieille chaudière par une pompe à chaleur moderne. Certains affirment que les renouvelables sont peu fiables, cependant, des avancées dans le stockage d’énergie réfutent cette idée. En effet, les batteries lithium-ion et les réseaux intelligents compensent les variations. De plus, l'ensemble des données montre une tendance globale à la baisse des coûts. Ainsi, la transition énergétique est non seulement possible, mais nécessaire.",
]

# Exemple d'utilisation
if __name__ == "__main__":
    result = evaluer_argument(ARGUMENTS_EXAMPLE[12])
    from pprint import pprint

    pprint(result)
