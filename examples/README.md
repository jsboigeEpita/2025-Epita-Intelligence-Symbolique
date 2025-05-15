# Exemples

Ce répertoire contient des exemples de textes et données utilisés dans le projet d'analyse argumentative. Ces exemples sont essentiels pour comprendre le fonctionnement du système et pour tester vos propres développements.

## Fichiers disponibles

### 1. exemple_sophisme.txt

Exemple de texte contenant plusieurs sophismes (erreurs de raisonnement) sur le thème de la régulation de l'intelligence artificielle.

**Description :**
Ce texte est un exemple fictif d'argumentation contenant plusieurs sophismes courants, notamment :
- Argument d'autorité : "Le professeur Dubois, éminent chercheur en informatique à l'Université de Paris, a récemment déclaré que..."
- Pente glissante : "D'abord, les algorithmes prendront le contrôle de nos systèmes financiers. Ensuite, ils s'infiltreront dans nos infrastructures critiques..."
- Appel à la popularité : "Un sondage récent montre que 78% des Français s'inquiètent des dangers potentiels de l'IA. Cette majorité écrasante prouve bien que la menace est réelle..."
- Faux dilemme : "Il n'y a que deux options possibles : soit nous imposons immédiatement un moratoire complet sur le développement de l'IA, soit nous acceptons la fin de la civilisation humaine..."

**Utilisation :**
Ce texte peut être utilisé pour tester les capacités d'analyse argumentative du système, en particulier la détection de sophismes par l'agent Informal.

```bash
# Exemple d'utilisation avec l'agent d'analyse informelle
python -c "from argumentiation_analysis.agents.informal.informal_agent import InformalAgent; \
           from argumentiation_analysis.core.llm_service import LLMService; \
           llm = LLMService(); \
           agent = InformalAgent(llm); \
           with open('examples/exemple_sophisme.txt', 'r') as f: \
               text = f.read(); \
           result = agent.analyze_informal_fallacies(text); \
           print(result)"
```

### 2. texte_sans_marqueurs.txt

Texte informatif sur la pensée critique sans sophismes évidents.

**Description :**
Ce texte présente une structure claire et bien construite sur le thème de la pensée critique. Il est caractérisé par :
- Une introduction claire du sujet
- Des définitions précises
- Des arguments logiques
- Des recommandations pratiques
- Une conclusion qui résume les points principaux

**Utilisation :**
Ce texte sert de "contrôle négatif" pour tester si l'agent peut correctement identifier l'absence de sophismes dans un texte bien construit. Il est particulièrement utile pour évaluer le taux de faux positifs du système.

```bash
# Exemple d'utilisation pour tester la précision du système
python scripts/execution/run_analysis.py --file examples/texte_sans_marqueurs.txt --mode verification
```

### 3. article_scientifique.txt

Article académique sur l'analyse d'arguments par NLP avec une structure formelle.

**Description :**
Cet article scientifique présente une structure formelle typique avec :
- Un résumé (abstract)
- Une introduction
- Une méthodologie
- Des résultats quantitatifs
- Une discussion
- Une conclusion

Il contient des données chiffrées et des références à des travaux antérieurs, ce qui en fait un excellent exemple pour tester la capacité du système à analyser un discours technique et à distinguer entre affirmations factuelles et interprétations.

**Utilisation :**
Ce texte est idéal pour tester les capacités d'analyse structurelle et la compréhension des arguments basés sur des données.

```bash
# Exemple d'utilisation pour l'analyse structurelle
python scripts/execution/run_analysis.py --file examples/article_scientifique.txt --mode structure
```

### 4. discours_politique.txt

Discours politique avec une structure rhétorique claire.

**Description :**
Ce discours politique présente une structure rhétorique typique avec :
- Une introduction qui établit le contact avec l'audience
- Une présentation des enjeux
- Une énumération de propositions concrètes
- Une conclusion qui appelle à l'action

Ce texte permet de tester la capacité de l'agent à analyser un discours persuasif qui utilise des techniques rhétoriques sans nécessairement tomber dans le sophisme.

**Utilisation :**
Particulièrement utile pour tester la distinction entre rhétorique légitime et sophismes.

```bash
# Exemple d'utilisation pour l'analyse rhétorique
python scripts/execution/run_analysis.py --file examples/discours_politique.txt --mode rhetorique
```

### 5. discours_avec_template.txt

Allocution présidentielle avec des marqueurs explicites de structure.

**Description :**
Cette allocution présidentielle est très structurée avec des marqueurs explicites :
- Formule d'introduction protocolaire
- Annonce explicite du plan ("J'aborderai trois points essentiels")
- Marqueurs d'énumération clairs ("Premièrement", "Deuxièmement", "Troisièmement")
- Conclusion formelle

Ce texte permet de tester la capacité de l'agent à suivre une structure argumentative très explicite.

**Utilisation :**
Idéal pour tester les capacités d'extraction de structure argumentative du système.

```bash
# Exemple d'utilisation pour l'extraction de structure
python scripts/execution/run_analysis.py --file examples/discours_avec_template.txt --mode extraction
```

## Guide de contribution pour les étudiants

### Ajout de nouveaux exemples

Pour enrichir la base d'exemples du projet, vous pouvez ajouter vos propres textes argumentatifs. Cela est particulièrement utile pour tester différents types d'arguments, de sophismes, ou de structures rhétoriques.

Pour ajouter de nouveaux exemples à ce répertoire, veuillez suivre ces directives :

1. **Nommage des fichiers** : 
   - Utilisez un nom descriptif avec le format `exemple_[type]_[sujet].txt`
   - Exemple : `exemple_ad_hominem_politique.txt`, `exemple_faux_dilemme_technologie.txt`

2. **Documentation** : 
   - Ajoutez une description du fichier dans ce README.md
   - Incluez les types de sophismes ou structures argumentatives présentes
   - Expliquez le contexte et l'objectif de l'exemple

3. **Format** : 
   - Préférez le format texte brut (.txt) pour la compatibilité maximale
   - Utilisez l'encodage UTF-8
   - Assurez-vous que le texte est correctement formaté (paragraphes, ponctuation)

4. **Taille** : 
   - Limitez la taille des exemples à quelques paragraphes pour faciliter les tests
   - Idéalement entre 200 et 1000 mots

5. **Contenu** : 
   - Assurez-vous que le contenu est approprié et ne contient pas de données sensibles
   - Évitez les contenus offensants ou controversés
   - Si vous utilisez du contenu externe, citez vos sources et assurez-vous de respecter les droits d'auteur

### Workflow de contribution

1. **Créez une branche** dans votre fork pour ajouter votre exemple :
   ```bash
   git checkout -b feature/nouvel-exemple
   ```

2. **Ajoutez votre fichier** dans le répertoire examples :
   ```bash
   # Créez votre fichier d'exemple
   touch examples/exemple_votre_type_votre_sujet.txt
   
   # Éditez le fichier avec votre contenu
   nano examples/exemple_votre_type_votre_sujet.txt
   ```

3. **Mettez à jour ce README.md** pour documenter votre exemple :
   ```bash
   nano examples/README.md
   ```

4. **Testez votre exemple** avec le système d'analyse :
   ```bash
   python run_analysis.py --file examples/exemple_votre_type_votre_sujet.txt
   ```

5. **Committez et poussez vos changements** :
   ```bash
   git add examples/exemple_votre_type_votre_sujet.txt examples/README.md
   git commit -m "Ajout d'un exemple sur [votre sujet] avec [types de sophismes]"
   git push origin feature/nouvel-exemple
   ```

6. **Créez une Pull Request** vers le dépôt principal

### Suggestions de nouveaux exemples à créer

Si vous cherchez des idées pour contribuer, voici quelques suggestions d'exemples qui seraient utiles au projet :

1. **Textes avec des sophismes spécifiques** :
   - Exemple centré sur l'homme de paille
   - Exemple centré sur le faux dilemme
   - Exemple centré sur l'appel à l'ignorance

2. **Textes de différents domaines** :
   - Argumentation scientifique
   - Débat politique
   - Publicité et marketing
   - Discussions éthiques

3. **Textes avec différentes structures** :
   - Arguments en chaîne
   - Arguments parallèles
   - Réfutations et contre-arguments

## Utilisation des exemples dans les tests

Les exemples de ce répertoire peuvent être utilisés dans les tests unitaires et d'intégration. Pour ce faire, importez-les comme suit :

```python
import os

def load_example(filename):
    """Charge un exemple depuis le répertoire examples."""
    example_path = os.path.join(os.path.dirname(__file__), '..', '..', 'examples', filename)
    with open(example_path, 'r', encoding='utf-8') as f:
        return f.read()

# Utilisation
text = load_example('exemple_sophisme.txt')
```

### Intégration dans vos propres agents

Si vous développez un nouvel agent, vous pouvez utiliser ces exemples pour tester ses capacités :

```python
from agents.core.votre_agent.votre_agent_definitions import setup_votre_agent
from core.llm_service import create_llm_service

async def test_avec_exemple():
    # Charger l'exemple
    with open('examples/exemple_sophisme.txt', 'r', encoding='utf-8') as f:
        texte = f.read()
    
    # Initialiser votre agent
    llm_service = create_llm_service()
    kernel, agent = await setup_votre_agent(llm_service)
    
    # Tester votre agent avec l'exemple
    resultat = await agent.votre_methode_analyse(texte)
    print(resultat)
```

## Cas d'utilisation avancés

### Analyse comparative

Vous pouvez utiliser les différents exemples pour effectuer une analyse comparative des performances du système :

```python
import os
import json
from argumentation_analysis.agents.informal.informal_agent import InformalAgent
from argumentation_analysis.core.llm_service import LLMService

def run_comparative_analysis():
    # Initialiser l'agent
    llm = LLMService()
    agent = InformalAgent(llm)
    
    # Liste des exemples à analyser
    examples = [
        'exemple_sophisme.txt',
        'texte_sans_marqueurs.txt',
        'article_scientifique.txt',
        'discours_politique.txt',
        'discours_avec_template.txt'
    ]
    
    # Analyser chaque exemple
    results = {}
    for example in examples:
        with open(f'examples/{example}', 'r', encoding='utf-8') as f:
            text = f.read()
        result = agent.analyze_informal_fallacies(text)
        results[example] = result
    
    # Sauvegarder les résultats
    with open('results/comparative_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    return results
```

### Génération de rapports

Vous pouvez générer des rapports détaillés à partir des analyses des exemples :

```python
from argumentation_analysis.utils.report_generator import generate_report

# Générer un rapport d'analyse pour un exemple
generate_report('examples/exemple_sophisme.txt', 'results/rapport_exemple_sophisme.md')
```

## Ressources pour créer de bons exemples

- [Liste des sophismes courants](https://fr.wikipedia.org/wiki/Liste_de_sophismes)
- [Guide d'argumentation](https://www.cairn.info/revue-l-argumentation-politique--9782200928261.htm)
- [Techniques rhétoriques](https://www.persee.fr/doc/comm_0588-8018_1970_num_16_1_1234)
- [Analyse du discours](https://www.erudit.org/fr/revues/as/2006-v30-n1-as1384/014702ar/)
- [Structures argumentatives](https://www.cairn.info/revue-hermes-la-revue-2011-1-page-25.htm)