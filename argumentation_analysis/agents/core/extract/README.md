# 📑 Agent d'Extraction pour l'Analyse Argumentative

Ce module fournit un agent d'extraction intelligent capable de proposer des extraits pertinents dans un texte source en se basant sur la dénomination de l'extrait et le contexte.

[Retour au README Agents](../README.md)

## Fonctionnalités

- **Extraction intelligente** : Propose des extraits pertinents à partir de la dénomination
- **Approche dichotomique** : Navigation efficace dans les textes volumineux
- **Réparation d'extraits** : Correction des bornes défectueuses
- **Validation automatique** : Vérification de la pertinence des extraits proposés
- **Intégration complète** : Compatible avec le système de chiffrement des configurations

## Architecture

Le module est organisé en plusieurs composants :

- `extract_agent.py` : Implémentation principale de l'agent d'extraction
- `extract_definitions.py` : Définitions des classes et structures de données
- `prompts.py` : Instructions et prompts pour les agents LLM

## Utilisation

### Initialisation de l'agent

```python
import asyncio
from agents.extract import setup_extract_agent

async def main():
    # Initialiser l'agent d'extraction
    kernel, extract_agent = await setup_extract_agent()
    
    # Utiliser l'agent...
    
asyncio.run(main())
```

### Extraction à partir d'une dénomination

```python
# Extraire un passage pertinent à partir d'une dénomination
result = await extract_agent.extract_from_name(source_info, "Définition du syllogisme")

if result.status == "valid":
    print(f"Extrait trouvé : {result.extracted_text}")
    print(f"Marqueur de début : {result.start_marker}")
    print(f"Marqueur de fin : {result.end_marker}")
else:
    print(f"Échec de l'extraction : {result.message}")
```

### Réparation d'un extrait existant

```python
# Réparer un extrait existant
result = await extract_agent.repair_extract(extract_definitions, source_idx, extract_idx)

if result.status == "valid":
    # Mettre à jour les marqueurs
    success = await extract_agent.update_extract_markers(
        extract_definitions, source_idx, extract_idx, result
    )
    if success:
        print("Extrait réparé avec succès")
```

### Ajout d'un nouvel extrait

```python
# Extraire un passage et l'ajouter comme nouvel extrait
result = await extract_agent.extract_from_name(source_info, "Critique de la raison pure")

if result.status == "valid":
    success, extract_idx = await extract_agent.add_new_extract(
        extract_definitions, source_idx, "Critique de la raison pure", result
    )
    if success:
        print(f"Nouvel extrait ajouté à l'index {extract_idx}")
```

## Approche dichotomique

Pour les textes volumineux, l'agent utilise une approche dichotomique qui :

1. Divise le texte en blocs de taille fixe (par défaut 500 lignes) avec chevauchement
2. Recherche des mots-clés de la dénomination dans chaque bloc
3. Analyse les blocs pertinents pour identifier les passages correspondant à la dénomination
4. Propose des bornes précises pour délimiter l'extrait

Cette approche permet de traiter efficacement des textes de grande taille, comme le corpus de discours d'Hitler.

## Intégration avec l'interface utilisateur

Ce module peut être intégré à l'interface utilisateur existante pour permettre aux utilisateurs de :

1. Proposer automatiquement des extraits à partir d'une dénomination
2. Réparer les extraits existants avec des bornes défectueuses
3. Valider la pertinence des extraits proposés

## Dépendances

- `semantic_kernel` : Pour l'utilisation des agents LLM
- Modules internes du projet :
  - `ui.config`, `ui.utils`, `ui.extract_utils` : Pour l'accès aux configurations et utilitaires
  - `core.llm_service` : Pour la création du service LLM