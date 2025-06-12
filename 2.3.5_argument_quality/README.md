# 2.3.5 - 📘 Agent d’Évaluation de la Qualité Argumentative

## ⚙️ Présentation

Cet agent analyse un texte argumentatif et évalue neuf **vertus argumentatives** (clarté, pertinence, présence de sources, réfutation constructive, structure logique, analogies, fiabilité des sources, exhaustivité, redondance faible). Chaque vertu est détectée via des heuristiques linguistiques et des métriques (ex : Flesch pour la clarté, connecteurs pour la structure, motifs regex pour les citations). Le résultat est une **note par vertu**, un **score global** et un **rapport détaillé**.

---

## 🚀 Installation

1. Installer les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

2. Télécharger le modèle linguistique français :

   ```bash
   python -m spacy download fr_core_news_sm
   ```

---

## 🧪 Utilisation simple (ligne de commande ou script)

```python
from agent import evaluer_argument

texte = "Votre argument ici…"
rapport = evaluer_argument(texte)
print(rapport)
```

Le module retourne un dictionnaire comprenant :

* `note_finale` et `note_moyenne`
* `scores_par_vertu` : note (0 à 1) pour chaque vertu
* `rapport_detaille` : commentaires explicatifs

---

## 🖥️ Interface graphique (PyQt5)

L’interface est disponible dans `main.py`. Pour l’utiliser :

```bash
python main.py
```

Fonctionnalités :

* Saisir du texte ou charger un fichier `.txt`
* Choisir un exemple prédéfini
* Cliquer sur **Évaluer**
* Visualiser un tableau des scores par vertu + note finale/moyenne

---

## 🔌 Intégration dans une autre application

Vous pouvez importer directement :

```python
from agent import evaluer_argument
```

* **Entrée** : `text` (str)
* **Sortie** : dictionnaire détaillé (dict)

Une intégration type RESTful API pourrait être :

```python
@app.post("/evaluer")
def api_evaluer(arg: TexteArgumentatif):
    return evaluer_argument(arg.texte)
```

---

## 🔧 Ameliorations possibles

* Ajouter des **vertus**
* Intégrer des modules basés sur apprentissage automatique (scikit‑learn, Transformers…)
* Ajouter des **tests unitaires** pour chaque détecteur

---


## 🖊️ Auteurs :
  * Maxime Cambou
  * Quentin Prunet
  * Jules Raitiere-Delsupexhe
  * Hugo Schreiber