import argumentation_analysis.core.environment
import json
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class ComplexSyntheticDataGenerator:
    """
    Génère des données synthétiques complexes pour les tests d'analyse rhétorique et d'authenticité.
    """

    def __init__(self):
        self.themes = ["la conscience artificielle", "l'éthique de la surveillance", "le libre arbitre à l'ère numérique"]
        self.philosophes = ["Kant", "Sartre", "Arendt", "Foucault", "Descartes"]
        self.sophismes = {
            "ad_hominem": "Attaquer l'adversaire plutôt que ses arguments.",
            "straw_man": "Dénaturer l'argument de l'adversaire pour le réfuter plus facilement.",
            "false_dichotomy": "Présenter deux options comme les seules possibles, alors qu'il en existe d'autres.",
            "slippery_slope": "Prétendre qu'une action entraînera inévitablement une série de conséquences négatives."
        }

    def _generate_caesared_text(self, text: str, key: int) -> str:
        """Chiffre un texte avec le chiffrement de César."""
        res = []
        for char in text:
            if 'a' <= char <= 'z':
                res.append(chr((ord(char) - ord('a') + key) % 26 + ord('a')))
            elif 'A' <= char <= 'Z':
                res.append(chr((ord(char) - ord('A') + key) % 26 + ord('A')))
            else:
                res.append(char)
        return "".join(res)

    def generate_single_scenario(self, complexity: str, scenario_id: int) -> Dict[str, Any]:
        """Génère un seul scénario de test complexe."""
        theme = random.choice(self.themes)
        philosophe = random.choice(self.philosophes)
        sophisme_type = random.choice(list(self.sophismes.keys()))

        base_text = f"La discussion sur {theme}, influencée par {philosophe}, atteint un point critique. "
        
        # 1. Données pour le raisonnement modal
        modal_reasoning = {
            "contexte": f"Analyse modale de la {theme}.",
            "contraintes_modales": [
                f"Il est nécessaire que toute intelligence artificielle respecte les principes de {philosophe}.",
                f"Il est possible qu'un système de surveillance devienne totalitaire.",
                f"Il est impossible de prouver le libre arbitre de manière purement empirique."
            ]
        }

        # 2. Données pour l'argumentation philosophique
        philosophical_argumentation = {
            "theme": theme,
            "levels": {
                "niveau_1_these": {"texte": f"La these principale est que {theme} est une inevitabilite technologique."},
                "niveau_2_antithese": {"texte": f"L'antithese, selon {philosophe}, est que cela detruit l'autonomie humaine."},
                "niveau_3_sophisme": {
                    "texte": "Dire que l'opposition à cette technologie vient de la peur du progrès est un sophisme.",
                    "sophismes_imbriques": [{"type": sophisme_type, "texte": self.sophismes[sophisme_type]}]
                }
            }
        }

        # 3. Données pour l'analyse rhétorique chiffrée
        decryption_key = random.randint(3, 10)
        rhetoric_text = f"La dialectique hégélienne de la {theme} révèle une synthèse paradoxale. C'est une progression métaphysique vers une conscience computationnelle."
        encrypted_content = self._generate_caesared_text(rhetoric_text, decryption_key)
        verification_hash = hashlib.md5(rhetoric_text.encode()).hexdigest()
        encrypted_rhetoric = {
            "encrypted_content": encrypted_content,
            "decryption_key": decryption_key,
            "verification_hash": verification_hash,
            "contexte": "Analyse rhétorique d'un texte chiffré sur la métaphysique."
        }
        
        complexity_score = random.uniform(0.9, 1.0) if complexity == 'high' else random.uniform(0.5, 0.8)

        scenario = {
            "id": f"complex_scenario_{scenario_id}",
            "metadata": {
                "complexity_level": complexity,
                "total_complexity_score": complexity_score,
                "complexity_signature": hashlib.sha256(f"{theme}{philosophe}{scenario_id}".encode()).hexdigest(),
                "generated_at": datetime.now().isoformat()
            },
            "arguments": [
                 {"id": "arg1", "type": "these", "content": philosophical_argumentation["levels"]["niveau_1_these"]["texte"]},
                 {"id": "arg2", "type": "antithese", "content": philosophical_argumentation["levels"]["niveau_2_antithese"]["texte"]},
            ],
            "modal_reasoning": modal_reasoning,
            "philosophical_argumentation": philosophical_argumentation,
            "encrypted_rhetoric": encrypted_rhetoric
        }
        return scenario

    def generate_multiple_scenarios(self, complexity: str = 'high', num_scenarios: int = 1) -> List[Dict[str, Any]]:
        """Génère plusieurs scénarios de test complexes."""
        return [self.generate_single_scenario(complexity, i) for i in range(num_scenarios)]

    def save_to_file(self, scenarios: List[Dict[str, Any]], output_dir: Path):
        """Sauvegarde les scénarios générés dans un fichier JSON."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = output_dir / f"complex_test_data_{timestamp}.json"
        
        # Comme la fonction dans le test ne prend qu'un seul scénario, nous sauvegardons le premier.
        # Idéalement, la logique devrait être alignée, mais nous nous adaptons au test existant.
        data_to_save = scenarios[0] if scenarios else {}

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"Données de test complexes sauvegardées dans : {file_path}")
        return file_path


if __name__ == '__main__':
    # Ceci permet de générer manuellement le fichier de données nécessaire pour le test.
    generator = ComplexSyntheticDataGenerator()
    scenarios = generator.generate_multiple_scenarios(complexity='high', num_scenarios=1)
    
    # Le test cherche le fichier dans "tests/" ou le répertoire parent. 
    # Nous le sauvegardons dans "tests/" pour être sûr.
    output_directory = Path(__file__).resolve().parent.parent.parent / "tests"
    generator.save_to_file(scenarios, output_directory)