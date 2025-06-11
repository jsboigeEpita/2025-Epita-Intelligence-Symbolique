# Guide des Exemples du Projet

Bienvenue dans le répertoire `examples/` ! Ce dossier centralise divers types d'exemples conçus pour vous aider à comprendre et à utiliser les différentes fonctionnalités de ce projet d'analyse argumentative. Vous y trouverez :

*   Des **scripts Python** illustrant l'utilisation des composants clés.
*   Des **notebooks Jupyter** offrant des tutoriels interactifs.
*   Des **fichiers textes** servant de données d'entrée pour les analyses.

## Structure du Répertoire et Contenu

Voici un aperçu des principaux sous-répertoires et de ce qu'ils contiennent :

### 📁 `examples/logic_agents/`
Ce répertoire contient des scripts Python démontrant l'utilisation et l'intégration des différents agents logiques développés dans le projet. Chaque script se concentre sur un type de logique ou une fonctionnalité spécifique.
*   [`logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0): Montre comment intégrer et utiliser les agents logiques via une API (si applicable).
*   [`logic_agents/combined_logic_example.py`](examples/logic_agents/combined_logic_example.py:0): Illustre l'utilisation combinée de plusieurs approches ou agents logiques.
*   [`logic_agents/first_order_logic_example.py`](examples/logic_agents/first_order_logic_example.py:0): Exemple d'utilisation de l'agent basé sur la logique du premier ordre.
*   [`logic_agents/modal_logic_example.py`](examples/logic_agents/modal_logic_example.py:0): Exemple d'utilisation de l'agent basé sur la logique modale.
*   [`logic_agents/propositional_logic_example.py`](examples/logic_agents/propositional_logic_example.py:0): Exemple d'utilisation de l'agent basé sur la logique propositionnelle.
    *   Pour une compréhension plus approfondie, consultez le guide sur les [exemples de logique propositionnelle](docs/guides/exemples_logique_propositionnelle.md).

Pour plus de détails sur l'utilisation générale des agents logiques, référez-vous au [guide d'utilisation des agents logiques](docs/guides/utilisation_agents_logiques.md).

### 📁 `examples/scripts_demonstration/`
Ce dossier regroupe des scripts Python conçus pour des démonstrations plus complètes et des cas d'usage spécifiques du système.
*   [`scripts_demonstration/demo_tweety_interaction_simple.py`](examples/scripts_demonstration/demo_tweety_interaction_simple.py:0): Un script simple illustrant l'interaction avec la bibliothèque Tweety.
*   [`scripts_demonstration/demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py:0): Un script de démonstration plus exhaustif des capacités du projet. Pour plus de détails sur ce script, consultez son [README dédié](examples/scripts_demonstration/README_DEMONSTRATION.md).
*   Consultez également le [README général de ce sous-dossier](examples/scripts_demonstration/README.md) pour plus d'informations.

### 📁 `examples/notebooks/`
Ici, vous trouverez des notebooks Jupyter qui fournissent des tutoriels interactifs et pas à pas pour explorer certaines fonctionnalités.
*   [`notebooks/api_logic_tutorial.ipynb`](examples/notebooks/api_logic_tutorial.ipynb:0): Un tutoriel sur l'utilisation de l'API des agents logiques.
*   [`notebooks/logic_agents_tutorial.ipynb`](examples/notebooks/logic_agents_tutorial.ipynb:0): Un tutoriel guidé sur l'utilisation des différents agents logiques.

### 📁 `examples/test_data/`
Ce répertoire contient des fichiers de données utilisés spécifiquement pour les tests automatisés ou des configurations d'exemples.
*   [`test_data/test_sophismes_complexes.txt`](examples/test_data/test_sophismes_complexes.txt:0): Un exemple de texte avec des sophismes complexes, utilisé pour les tests.

### 📄 Exemples de Textes pour l'Analyse (à la racine de `examples/`)
Ces fichiers `.txt` situés directement dans le répertoire `examples/` sont des exemples de discours, d'articles ou d'argumentations destinés à être analysés par le système.
*   [`exemple_sophisme.txt`](examples/exemple_sophisme.txt:0): Texte contenant plusieurs sophismes courants.
*   [`texte_sans_marqueurs.txt`](examples/texte_sans_marqueurs.txt:0): Texte informatif sans sophismes évidents, servant de contrôle.
*   [`article_scientifique.txt`](examples/article_scientifique.txt:0): Article académique avec une structure formelle.
*   [`discours_politique.txt`](examples/discours_politique.txt:0): Discours politique avec une structure rhétorique.
*   [`discours_avec_template.txt`](examples/discours_avec_template.txt:0): Allocution avec des marqueurs explicites de structure.
*   [`exemple_sophismes_avances.txt`](examples/exemple_sophismes_avances.txt:0): Texte enrichi avec une variété de sophismes et annotations.
*   [`analyse_structurelle_complexe.txt`](examples/analyse_structurelle_complexe.txt:0): Argumentation complexe avec structure hiérarchique.

Pour des détails sur l'utilisation et le contenu de ces fichiers textes, ainsi que pour un guide de contribution à ces exemples textuels, veuillez vous référer à la section "Guide Détaillé des Exemples de Textes et Contribution" plus bas dans ce document.

## Comment Exécuter les Exemples

### Prérequis
Avant de lancer les exemples, assurez-vous que votre environnement de développement est correctement configuré. Cela peut impliquer :
1.  L'installation des dépendances du projet (consultez le [`GUIDE_INSTALLATION_ETUDIANTS.md`](GUIDE_INSTALLATION_ETUDIANTS.md:0)).
2.  L'activation de l'environnement virtuel du projet, par exemple avec le script [`activate_project_env.ps1`](activate_project_env.ps1:0) (pour PowerShell) ou [`activate_project_env.sh`](activate_project_env.sh:0) (pour Bash).
    ```powershell
    # Exemple pour PowerShell
    .\activate_project_env.ps1
    ```
3.  Certains scripts, notamment ceux interagissant avec des services externes (comme les LLMs), peuvent nécessiter la configuration de clés API via un fichier `.env`. Référez-vous à la documentation spécifique de ces scripts ou aux guides pertinents.

### Exécution des Scripts Python
Pour exécuter un script Python, utilisez la commande `python` suivie du chemin vers le script :
```bash
python examples/logic_agents/propositional_logic_example.py
python examples/scripts_demonstration/demo_tweety_interaction_simple.py
```

### Utilisation des Notebooks Jupyter
Pour utiliser les notebooks :
1.  Assurez-vous que Jupyter Notebook ou JupyterLab est installé dans votre environnement.
2.  Lancez Jupyter depuis votre terminal à la racine du projet :
    ```bash
    jupyter notebook
    # ou
    jupyter lab
    ```
3.  Naviguez jusqu'au répertoire `examples/notebooks/` et ouvrez le notebook de votre choix.

## Guide Détaillé des Exemples de Textes et Contribution

Ce répertoire contient des exemples de textes et données utilisés dans le projet d'analyse argumentative. Ces exemples sont essentiels pour comprendre le fonctionnement du système et pour tester vos propres développements.

### Fichiers disponibles

#### 1. exemple_sophisme.txt

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

#### 2. texte_sans_marqueurs.txt

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

#### 3. article_scientifique.txt

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

#### 4. discours_politique.txt

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

#### 5. discours_avec_template.txt

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

#### 6. exemple_sophismes_avances.txt

Exemple enrichi de texte contenant une variété de sophismes avec annotations et cas d'utilisation avancés.

**Description :**
Ce texte est une version enrichie et annotée de l'exemple de sophismes sur la régulation de l'intelligence artificielle. Il contient :
- Des sophismes clairement identifiés et expliqués
- Une structure argumentative plus complexe avec introduction, développement, conclusion et réfutation
- Des sophismes plus subtils et imbriqués
- Des notes explicatives pour l'analyse

**Utilisation :**
Ce texte est particulièrement utile pour des cas d'utilisation avancés comme :
- La détection de sophismes imbriqués
- L'analyse de la structure argumentative globale
- L'évaluation de la cohérence des arguments
- La reconstruction d'arguments valides à partir d'arguments fallacieux

```bash
# Exemple d'utilisation pour l'analyse avancée
python scripts/execution/run_analysis.py --file examples/exemple_sophismes_avances.txt --mode complet
```

#### 7. analyse_structurelle_complexe.txt

Exemple détaillé d'une argumentation complexe avec structure hiérarchique et relations argumentatives variées.

**Description :**
Ce document présente un débat structuré sur la taxation des robots avec :
- Une thèse principale clairement énoncée
- Trois arguments principaux de premier niveau
- Des sous-arguments et preuves pour chaque argument principal
- Des objections et réfutations
- Une structure hiérarchique explicite
- Des connecteurs logiques variés

**Utilisation :**
Cet exemple est conçu pour tester les capacités avancées d'analyse structurelle :
- Extraction de la structure hiérarchique des arguments
- Identification des relations entre arguments (support, objection, réfutation)
- Évaluation de la cohérence structurelle
- Visualisation de la structure argumentative

```bash
# Exemple d'utilisation pour l'analyse structurelle avancée
python scripts/execution/run_analysis.py --file examples/analyse_structurelle_complexe.txt --mode structure
```

### Guide de contribution pour les étudiants (Exemples de Textes)

#### Ajout de nouveaux exemples de textes

Pour enrichir la base d'exemples du projet, vous pouvez ajouter vos propres textes argumentatifs. Cela est particulièrement utile pour tester différents types d'arguments, de sophismes, ou de structures rhétoriques.

Pour ajouter de nouveaux exemples à ce répertoire, veuillez suivre ces directives :

1. **Nommage des fichiers** : 
   - Utilisez un nom descriptif avec le format `exemple_[type]_[sujet].txt`
   - Exemple : `exemple_ad_hominem_politique.txt`, `exemple_faux_dilemme_technologie.txt`

2. **Documentation** : 
   - Ajoutez une description du fichier dans ce README.md (dans la section "Fichiers disponibles")
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

#### Workflow de contribution (Exemples de Textes)

1. **Créez une branche** dans votre fork pour ajouter votre exemple :
   ```bash
   git checkout -b feature/nouvel-exemple-texte
   ```

2. **Ajoutez votre fichier** dans le répertoire `examples/` :
   ```bash
   # Créez votre fichier d'exemple
   touch examples/exemple_votre_type_votre_sujet.txt
   
   # Éditez le fichier avec votre contenu
   # nano examples/exemple_votre_type_votre_sujet.txt 
   ```

3. **Mettez à jour ce README.md** pour documenter votre exemple :
   ```bash
   # nano examples/README.md
   ```

4. **Testez votre exemple** avec le système d'analyse :
   ```bash
   python scripts/execution/run_analysis.py --file examples/exemple_votre_type_votre_sujet.txt
   ```

5. **Committez et poussez vos changements** :
   ```bash
   git add examples/exemple_votre_type_votre_sujet.txt examples/README.md
   git commit -m "Ajout d'un exemple de texte sur [votre sujet] avec [types de sophismes]"
   git push origin feature/nouvel-exemple-texte
   ```

6. **Créez une Pull Request** vers le dépôt principal

#### Suggestions de nouveaux exemples de textes à créer

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

### Utilisation des exemples de textes dans les tests

Les exemples de ce répertoire peuvent être utilisés dans les tests unitaires et d'intégration. Pour ce faire, importez-les comme suit :

```python
import os

def load_example(filename):
    """Charge un exemple depuis le répertoire examples."""
    # Ajustez le chemin si ce code est appelé depuis un sous-répertoire de tests
    base_dir = os.path.dirname(os.path.abspath(__file__))
    example_path = os.path.join(base_dir, '..', 'examples', filename) # Exemple: si tests/ est au même niveau que examples/
    # Si la structure est différente, adaptez les '..' ou le chemin de base.
    # Pour un appel depuis la racine du projet, ce serait plus simple :
    # example_path = os.path.join('examples', filename)
    with open(example_path, 'r', encoding='utf-8') as f:
        return f.read()

# Utilisation
# text = load_example('exemple_sophisme.txt')
```

### Intégration dans vos propres agents (avec les exemples de textes)

Si vous développez un nouvel agent, vous pouvez utiliser ces exemples pour tester ses capacités :

```python
# from agents.core.votre_agent.votre_agent_definitions import setup_votre_agent # Adaptez l'import
# from core.llm_service import create_llm_service # Adaptez l'import

async def test_avec_exemple_texte():
    # Charger l'exemple
    with open('examples/exemple_sophisme.txt', 'r', encoding='utf-8') as f:
        texte = f.read()
    
    # Initialiser votre agent (exemple)
    # llm_service = create_llm_service()
    # kernel, agent = await setup_votre_agent(llm_service)
    
    # Tester votre agent avec l'exemple
    # resultat = await agent.votre_methode_analyse(texte)
    # print(resultat)
    pass # Placeholder
```

### Cas d'utilisation avancés (avec les exemples de textes)

#### Analyse comparative

Vous pouvez utiliser les différents exemples pour effectuer une analyse comparative des performances du système :

```python
import os
import json
# from argumentation_analysis.agents.informal.informal_agent import InformalAgent # Adaptez l'import
# from argumentation_analysis.core.llm_service import LLMService # Adaptez l'import

def run_comparative_analysis_text_examples():
    # Initialiser l'agent (exemple)
    # llm = LLMService()
    # agent = InformalAgent(llm)
    
    # Liste des exemples à analyser
    examples_texts = [
        'exemple_sophisme.txt',
        'texte_sans_marqueurs.txt',
        'article_scientifique.txt',
        'discours_politique.txt',
        'discours_avec_template.txt'
    ]
    
    # Analyser chaque exemple
    results = {}
    # for example_file in examples_texts:
    #     with open(f'examples/{example_file}', 'r', encoding='utf-8') as f:
    #         text = f.read()
    #     result = agent.analyze_informal_fallacies(text) # Adaptez la méthode d'analyse
    #     results[example_file] = result
    
    # Sauvegarder les résultats
    # output_dir = 'results'
    # os.makedirs(output_dir, exist_ok=True)
    # with open(os.path.join(output_dir, 'comparative_analysis_texts.json'), 'w', encoding='utf-8') as f:
    #     json.dump(results, f, indent=2)
    
    # return results
    pass # Placeholder
```

#### Génération de rapports

Vous pouvez générer des rapports détaillés à partir des analyses des exemples :

```python
# from argumentation_analysis.utils.report_generator import generate_report # Adaptez l'import

# Générer un rapport d'analyse pour un exemple
# generate_report('examples/exemple_sophisme.txt', 'results/rapport_exemple_sophisme.md')
pass # Placeholder
```

### Ressources pour créer de bons exemples de textes

- [Liste des sophismes courants](https://fr.wikipedia.org/wiki/Liste_de_sophismes)
- [Guide d'argumentation](https://www.cairn.info/revue-l-argumentation-politique--9782200928261.htm)
- [Techniques rhétoriques](https://www.persee.fr/doc/comm_0588-8018_1970_num_16_1_1234)
- [Analyse du discours](https://www.erudit.org/fr/revues/as/2006-v30-n1-as1384/014702ar/)
- [Structures argumentatives](https://www.cairn.info/revue-hermes-la-revue-2011-1-page-25.htm)

## Distinction avec `argumentation_analysis/examples/`
⚠️ **Note importante** : Ce répertoire (`examples/`) contient des exemples d'utilisation, des scripts de démonstration, des notebooks tutoriels et des données textuelles pour tester le système. Il ne doit pas être confondu avec le dossier `argumentation_analysis/examples/` qui pourrait contenir des exemples de code plus bas niveau ou spécifiques à l'implémentation interne des modules d'analyse.

| Ce dossier (`examples/`)                                  | Dossier `argumentation_analysis/examples/` (si existant et utilisé ainsi) |
|-----------------------------------------------------------|--------------------------------------------------------------------------|
| Contient des scripts `.py`, notebooks `.ipynb`, textes `.txt` | Pourrait contenir des fichiers Python (`.py`) spécifiques à des modules   |
| Exemples d'utilisation, tutoriels, démos, données d'entrée | Exemples de code d'implémentation interne ou tests unitaires de bas niveau |
| Utilisé pour apprendre à utiliser le système et voir des démos | Utilisé par les développeurs du cœur du système                          |

---
*Ce README a pour but de vous guider à travers les exemples fournis. N'hésitez pas à explorer les différents fichiers et scripts pour mieux comprendre le fonctionnement du projet.*