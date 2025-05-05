# Exemples

Ce répertoire contient des exemples de textes et données utilisés dans le projet d'analyse argumentative.

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

## Ajout de nouveaux exemples

Pour ajouter de nouveaux exemples à ce répertoire, veuillez suivre ces directives :

1. **Nommage des fichiers** : Utilisez un nom descriptif avec le format `exemple_[type]_[sujet].txt`
2. **Documentation** : Ajoutez une description du fichier dans ce README.md
3. **Format** : Préférez le format texte brut (.txt) pour la compatibilité maximale
4. **Taille** : Limitez la taille des exemples à quelques paragraphes pour faciliter les tests
5. **Contenu** : Assurez-vous que le contenu est approprié et ne contient pas de données sensibles

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