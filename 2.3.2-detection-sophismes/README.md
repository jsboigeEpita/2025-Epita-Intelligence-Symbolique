# Pipeline de Détection de Sophismes en Français

Ce projet fournit un pipeline NLP (Traitement du Langage Naturel) modulaire et explicable pour la détection de sophismes argumentatifs dans des textes en français. Il est conçu pour des applications à enjeux élevés où la précision et la transparence sont essentielles.

## Architecture

Le pipeline suit une approche hybride en plusieurs étapes :

1.  **Extraction d'Arguments (Argument Mining)** : Identifie les affirmations (claims) et les prémisses (premises) en utilisant `spaCy` et des motifs basés sur des règles, adaptés au discours français.
2.  **Détection Parallèle** :
    - **Moteur Neuronal** : Un transformeur affiné (fine-tuned) (CamemBERT-large) effectue une classification de sophismes à étiquette unique (single-label).
    - **Moteur Symbolique** : Un système robuste basé sur des règles utilisant `spaCy` pour correspondre à des schémas de sophismes français connus.
3.  **Ensemble & Vérification** : Combine les sorties neuronales et symboliques, en tenant compte des scores de confiance et en donnant la priorité aux détections symboliques le cas échéant. Ce module standardise également les noms des sophismes pour un rapport cohérent.
4.  **Génération d'Explications** : Un modèle génératif (par exemple, T5-Français, actuellement basé sur des modèles/templates) produit des justifications claires et lisibles en français.

## Modules

- `fallacy_pipeline.py` : L'orchestrateur principal du pipeline, intégrant tous les modules.
- `symbolic_rules.py` : Contient les règles de correspondance de motifs pour le moteur symbolique.
- `argument_mining_rules.py` : Définit les motifs pour identifier les affirmations et les prémisses dans l'étape d'extraction d'arguments.
- `train_camembert.py` : Script pour affiner (fine-tuning) le modèle CamemBERT sur l'ensemble de données de sophismes en français.
- `benchmark_model.py` : Script pour évaluer les performances du modèle CamemBERT affiné sur l'ensemble de test.
- `run_cli.py` : Un script d'interface en ligne de commande pour exécuter facilement le pipeline sur des textes personnalisés.
- `requirements.txt` : Liste les paquets Python nécessaires.

## Installation et Utilisation

1.  **Installer les Dépendances** :
    ```bash
    pip install -r requirements.txt
    pip install accelerate>=0.26.0 # Requis pour Trainer
    pip install sentencepiece # Requis pour le tokenizer CamemBERT
    python -m spacy download fr_core_news_lg
    ```

2.  **Entraîner le Modèle Neuronal (Optionnel mais Recommandé)** :
    Le `fallacy_pipeline.py` s'attend à un modèle CamemBERT affiné. Si vous ne l'avez pas encore entraîné, ou si vous souhaitez le ré-entraîner :
    ```bash
    python train_camembert.py
    ```
    Cela sauvegardera le modèle affiné dans `./fine_tuned_camembert/`.
    **Note** : Le modele est lourd et pese environ 1.8Go. Le temps d'entrainement peut egalement etre consequent.

3.  **Évaluer le Modèle Neuronal (Optionnel)** :
    Pour évaluer les performances du modèle affiné sur l'ensemble de données de test :
    ```bash
    python benchmark_model.py
    ```

4.  **Exécuter le Pipeline via la CLI** :
    Pour analyser un argument textuel en français :
    ```bash
    python run_cli.py "Votre argument en français ici."
    ```
    Exemple :
    ```bash
    python run_cli.py "Un expert a dit à la télévision que l'IA est la plus grande menace pour l'humanité, donc ça doit être vrai. On ne peut pas faire confiance aux politiciens."
    ```

## Modèles et Entraînement

- **Extraction d'Arguments** : Utilise le modèle `fr_core_news_lg` de `spaCy` et des motifs de règles personnalisés définis dans `argument_mining_rules.py`.
- **Classification Neuronale de Sophismes** :
    - **Modèle** : `camembert/camembert-large` est utilisé comme modèle de base.
    - **Jeu de données** : Les fichiers `french_train_data.parquet` et `french_val_data.parquet` sont utilisés. Ils contiennent une colonne `text` et une seule colonne `labels` avec des étiquettes entières pour la classification à étiquette unique.
    - **Entraînement** : Le script `train_camembert.py` affine le modèle en utilisant `CrossEntropyLoss` (géré implicitement par `Trainer` pour la classification à étiquette unique) et l'évalue en utilisant le F1-score micro/macro et l'accuracy.
- **Génération d'Explications** : Utilise actuellement des justifications basées sur des modèles (templates). Pour des explications plus dynamiques, un modèle génératif affiné (par exemple, T5-Français) serait nécessaire, entraîné sur des paires `(argument, type_de_sophisme) -> explication`.

## Moteur Symbolique

Le moteur symbolique utilise des règles définies dans `symbolic_rules.py`. Ces règles sont basées sur des motifs linguistiques courants trouvés dans les sophismes en français. Le moteur a été enrichi avec davantage de motifs pour :
- Attaque personnelle (Ad Hominem)
- Pente glissante (Slippery Slope)
- Généralisation hâtive (Hasty Generalization)
- Appel à la tradition (Appeal to Tradition)
- Argument d'autorité (Appeal to Authority)
Le moteur peut être étendu en ajoutant de nouvelles règles.

## Prétraitement

Les étapes de prétraitement sont gérées implicitement by les bibliothèques choisies :
- **`transformers` (pour CamemBERT)** : Le `CamembertTokenizer` effectue la tokenisation, la segmentation en sous-mots (subword) et la normalisation interne (y compris la gestion de la casse) dans le cadre de sa méthode `encode_plus`.
- **`spaCy` (pour l'Extraction d'Arguments et la Correspondance Symbolique)** : Lorsque `nlp(text)` est appelé, `spaCy` effectue la tokenisation, l'étiquetage morpho-syntaxique (POS tagging) et la lemmatisation. Pour les règles symboliques, les motifs exploitent souvent les attributs `LOWER` ou `LEMMA`, rendant les correspondances insensibles à la casse là où c'est spécifié.
