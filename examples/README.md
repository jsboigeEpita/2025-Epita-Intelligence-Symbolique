# Exemples

Ce répertoire contient des exemples de textes et données utilisés dans le projet d'analyse argumentative. Ces exemples sont essentiels pour comprendre le fonctionnement du système et pour tester vos propres développements.

## Fichiers disponibles

### 1. exemple_sophisme.txt

Exemple de texte contenant plusieurs sophismes (erreurs de raisonnement) sur le thème de la régulation de l'intelligence artificielle.

**Description :**
Ce texte est un exemple fictif d'argumentation contenant plusieurs sophismes courants, notamment :
- Argument d'autorité
- Pente glissante
- Appel à la popularité
- Corrélation impliquant causalité
- Faux dilemme

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

## Ressources pour créer de bons exemples

- [Liste des sophismes courants](https://fr.wikipedia.org/wiki/Liste_de_sophismes)
- [Guide d'argumentation](https://www.cairn.info/revue-l-argumentation-politique--9782200928261.htm)
- [Techniques rhétoriques](https://www.persee.fr/doc/comm_0588-8018_1970_num_16_1_1234)