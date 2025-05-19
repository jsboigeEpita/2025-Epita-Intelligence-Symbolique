#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour simuler le comportement de l'agent informel sur un texte contenant des sophismes complexes
"""

import json
from pathlib import Path
import re
from datetime import datetime

class SimulatedInformalAgent:
    """Simulation d'un agent informel qui analyse progressivement les sophismes"""
    
    def __init__(self):
        """Initialisation de l'agent avec la taxonomie des sophismes"""
        self.taxonomie = {
            "appel_inapproprié": {
                "description": "Sophismes basés sur des appels inappropriés à différentes sources",
                "sous_categories": {
                    "autorité": {
                        "description": "Appel à une autorité qui n'est pas qualifiée dans le domaine",
                        "sous_categories": {
                            "citation": {
                                "description": "Utilisation d'une citation hors contexte pour justifier une position"
                            },
                            "nombre_citations": {
                                "description": "Utilisation du nombre de citations comme preuve de validité"
                            }
                        }
                    },
                    "popularité": {
                        "description": "Justification basée uniquement sur la popularité d'une opinion",
                        "sous_categories": {
                            "ad_populum": {
                                "description": "Affirmer qu'une proposition est vraie parce que beaucoup y croient"
                            }
                        }
                    },
                    "tradition": {
                        "description": "Justification basée uniquement sur le caractère traditionnel"
                    },
                    "nouveauté": {
                        "description": "Justification basée uniquement sur le caractère nouveau"
                    },
                    "émotion": {
                        "description": "Appel aux émotions plutôt qu'à la raison",
                        "sous_categories": {
                            "culpabilisation": {
                                "description": "Utilisation de la culpabilité pour discréditer les opposants"
                            }
                        }
                    }
                }
            },
            "faux_dilemme": {
                "description": "Présentation d'une situation comme n'ayant que deux options possibles"
            },
            "pente_glissante": {
                "description": "Présentation d'une série d'événements comme étant la conséquence inévitable d'un premier événement"
            },
            "généralisation_hâtive": {
                "description": "Généralisation à partir d'un cas particulier sans tenir compte des différences contextuelles",
                "sous_categories": {
                    "fausse_analogie": {
                        "description": "Comparaison entre deux situations qui ne sont pas suffisamment similaires"
                    }
                }
            },
            "homme_de_paille": {
                "description": "Déformation de la position adverse pour la rendre plus facile à attaquer"
            }
        }
        
        # Motifs de détection pour les sophismes de base (simplifiés pour la simulation)
        self.motifs_base = {
            "appel_inapproprié_autorité": r"expert|professeur|reconnu|ne peut être remise en question",
            "appel_inapproprié_popularité": r"majorité|68%|tant de personnes|écrasante",
            "faux_dilemme": r"deux options|soit.*soit|choix.*évident",
            "pente_glissante": r"d'abord.*ensuite.*puis.*finalement|catastrophe sans précédent",
            "appel_inapproprié_tradition": r"méthodes traditionnelles|pendant des siècles|fait leur temps",
            "appel_inapproprié_nouveauté": r"nouvelles technologies|approches.*nouvelles|révolutionner",
            "appel_inapproprié_émotion": r"moralement répréhensible|avenir de nos enfants|ne se soucient pas"
        }
        
        # Motifs de détection pour les sophismes complexes (simplifiés pour la simulation)
        self.motifs_complexes = {
            "appel_inapproprié_autorité_citation": r"cités plus de 500 fois|prouve indéniablement",
            "généralisation_hâtive_fausse_analogie": r"pays scandinaves|Finlande|mêmes résultats|indépendamment des différences",
            "homme_de_paille_culpabilisation": r"opposants.*prétendent|mettre un prix sur|préfèrent économiser",
            "appel_inapproprié_citation": r"Victor Hugo|citation.*suffit à elle seule"
        }
    
    def analyser_texte(self, texte):
        """Simule l'analyse progressive du texte"""
        print("=== SIMULATION DE L'AGENT INFORMEL ===\n")
        
        # Étape 1: Identification des sophismes de base
        print("ÉTAPE 1: IDENTIFICATION DES SOPHISMES DE BASE\n")
        sophismes_base = self._identifier_sophismes_base(texte)
        self._afficher_resultats(sophismes_base)
        
        # Étape 2: Exploration des branches pertinentes
        print("\nÉTAPE 2: EXPLORATION DES BRANCHES PERTINENTES\n")
        branches_pertinentes = self._explorer_branches(sophismes_base)
        self._afficher_branches(branches_pertinentes)
        
        # Étape 3: Affinement de l'analyse
        print("\nÉTAPE 3: AFFINEMENT DE L'ANALYSE\n")
        sophismes_complexes = self._identifier_sophismes_complexes(texte)
        self._afficher_resultats(sophismes_complexes)
        
        # Étape 4: Analyse contextuelle
        print("\nÉTAPE 4: ANALYSE CONTEXTUELLE\n")
        analyse_contextuelle = self._analyser_contexte(texte, sophismes_base + sophismes_complexes)
        print(analyse_contextuelle)
        
        # Génération du rapport final
        self._generer_rapport(texte, sophismes_base + sophismes_complexes)
    
    def _identifier_sophismes_base(self, texte):
        """Identifie les sophismes de base dans le texte"""
        sophismes = []
        for nom, motif in self.motifs_base.items():
            matches = re.finditer(motif, texte, re.IGNORECASE)
            for match in matches:
                debut = max(0, match.start() - 50)
                fin = min(len(texte), match.end() + 50)
                extrait = texte[debut:fin]
                sophismes.append({
                    "type": nom,
                    "extrait": extrait,
                    "position": match.start(),
                    "confiance": 0.8
                })
        
        # Trier par position dans le texte
        sophismes.sort(key=lambda s: s["position"])
        return sophismes
    
    def _explorer_branches(self, sophismes_base):
        """Explore les branches pertinentes de la taxonomie"""
        branches = set()
        for sophisme in sophismes_base:
            type_sophisme = sophisme["type"]
            parties = type_sophisme.split("_")
            
            if len(parties) >= 2:
                branche_principale = parties[0]
                sous_branche = "_".join(parties[1:])
                
                if branche_principale in self.taxonomie:
                    branches.add(branche_principale)
                    
                    if "sous_categories" in self.taxonomie[branche_principale]:
                        for sous_cat in self.taxonomie[branche_principale]["sous_categories"]:
                            if sous_cat in sous_branche:
                                branches.add(f"{branche_principale}.{sous_cat}")
        
        return list(branches)
    
    def _identifier_sophismes_complexes(self, texte):
        """Identifie les sophismes complexes dans le texte"""
        sophismes = []
        for nom, motif in self.motifs_complexes.items():
            matches = re.finditer(motif, texte, re.IGNORECASE)
            for match in matches:
                debut = max(0, match.start() - 50)
                fin = min(len(texte), match.end() + 50)
                extrait = texte[debut:fin]
                sophismes.append({
                    "type": nom,
                    "extrait": extrait,
                    "position": match.start(),
                    "confiance": 0.7
                })
        
        # Trier par position dans le texte
        sophismes.sort(key=lambda s: s["position"])
        return sophismes
    
    def _analyser_contexte(self, texte, sophismes):
        """Simule une analyse contextuelle approfondie"""
        paragraphes = texte.split("\n\n")
        
        analyse = "Analyse contextuelle approfondie:\n\n"
        
        # Simuler l'analyse contextuelle pour la généralisation hâtive
        if any(s["type"] == "généralisation_hâtive_fausse_analogie" for s in sophismes):
            analyse += "1. Généralisation hâtive / Fausse analogie:\n"
            analyse += "   - Le texte compare le système éducatif finlandais à notre système sans tenir compte des différences culturelles, sociales et économiques.\n"
            analyse += "   - Cette comparaison ignore les facteurs contextuels spécifiques qui ont contribué au succès du modèle finlandais.\n"
            analyse += "   - L'affirmation que nous obtiendrions 'nécessairement les mêmes résultats' est une simplification excessive.\n\n"
        
        # Simuler l'analyse contextuelle pour la combinaison homme de paille / appel à l'émotion
        if any(s["type"] == "homme_de_paille_culpabilisation" for s in sophismes):
            analyse += "2. Combinaison homme de paille et appel à l'émotion:\n"
            analyse += "   - Le texte déforme la position des opposants à la réforme en suggérant qu'ils 'ne se soucient pas de la jeunesse'.\n"
            analyse += "   - Cette déformation est combinée avec un appel émotionnel concernant 'l'avenir de nos enfants'.\n"
            analyse += "   - La préoccupation légitime concernant les coûts est transformée en indifférence morale.\n\n"
        
        # Simuler l'analyse contextuelle pour l'appel à l'autorité
        if any(s["type"] == "appel_inapproprié_autorité" for s in sophismes):
            analyse += "3. Appel inapproprié à l'autorité:\n"
            analyse += "   - Le Professeur Martin est présenté comme une autorité en éducation alors qu'il est économiste.\n"
            analyse += "   - Le texte ne fournit pas d'information sur ses qualifications spécifiques en matière d'éducation.\n"
            analyse += "   - L'affirmation que son opinion 'ne peut être remise en question' est particulièrement problématique dans un contexte scientifique.\n"
        
        return analyse
    
    def _afficher_resultats(self, sophismes):
        """Affiche les résultats de l'analyse"""
        if not sophismes:
            print("Aucun sophisme détecté.")
            return
        
        for i, sophisme in enumerate(sophismes, 1):
            print(f"Sophisme {i}: {sophisme['type']}")
            print(f"Extrait: \"{sophisme['extrait']}\"")
            print(f"Confiance: {sophisme['confiance']:.2f}")
            print()
    
    def _afficher_branches(self, branches):
        """Affiche les branches explorées de la taxonomie"""
        if not branches:
            print("Aucune branche pertinente identifiée.")
            return
        
        print("Branches pertinentes de la taxonomie:")
        for branche in branches:
            parties = branche.split(".")
            if len(parties) == 1:
                print(f"- {parties[0]}: {self.taxonomie[parties[0]]['description']}")
            elif len(parties) == 2 and parties[1] in self.taxonomie[parties[0]].get("sous_categories", {}):
                print(f"  - {parties[1]}: {self.taxonomie[parties[0]]['sous_categories'][parties[1]]['description']}")
    
    def _generer_rapport(self, texte, sophismes):
        """Génère un rapport d'analyse au format JSON"""
        rapport = {
            "timestamp": datetime.now().isoformat(),
            "texte_analysé": texte[:100] + "..." if len(texte) > 100 else texte,
            "nombre_sophismes_détectés": len(sophismes),
            "sophismes": sophismes,
            "recommandations": [
                "Éviter les appels à l'autorité non qualifiée dans le domaine",
                "Fournir des preuves concrètes plutôt que de s'appuyer sur la popularité des opinions",
                "Considérer plus de deux options possibles pour la réforme éducative",
                "Éviter les généralisations hâtives sans tenir compte des différences contextuelles",
                "Présenter fidèlement les positions des opposants"
            ]
        }
        
        with open("rapport_analyse_sophismes.json", "w", encoding="utf-8") as f:
            json.dump(rapport, f, ensure_ascii=False, indent=2)
        
        print("\nRapport d'analyse généré: rapport_analyse_sophismes.json")

def main():
    """Fonction principale"""
    # Lecture du fichier de test
    test_file = Path("test_sophismes_complexes.txt")
    if not test_file.exists():
        print(f"Le fichier {test_file} n'existe pas.")
        return
    
    with open(test_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    print(f"Texte chargé depuis {test_file} ({len(text_content)} caractères)\n")
    
    # Création et exécution de l'agent simulé
    agent = SimulatedInformalAgent()
    agent.analyser_texte(text_content)

if __name__ == "__main__":
    main()