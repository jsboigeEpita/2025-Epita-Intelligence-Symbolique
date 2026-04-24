# État Actuel du Projet Python

Ce document décrit l'état actuel du projet Python, en mettant l'accent sur les fonctionnalités stables et les limitations connues, notamment concernant l'intégration avec JPype et Tweety.

## 1. Fonctionnalités Python Stables et Testées (via Mocks)

Les modules et classes Python suivants sont considérés comme stables et ont été rigoureusement testés à l'aide de mocks, garantissant leur fonctionnement indépendant de la JVM réelle :

*   **`argumentation_analysis/` (Modules d'analyse d'argumentation) :**
    *   Les classes et fonctions principales pour l'analyse rhétorique, la détection des sophismes, et l'évaluation de la sévérité sont fonctionnelles.
    *   Les agents d'analyse (ex: `FallacyAnalyzer`, `ContextualFallacyAnalyzer`) sont opérationnels avec des données mockées.
    *   Les méthodes d'extraction et de traitement des définitions sont stables.
*   **`scripts/` (Utilitaires et Scripts) :**
    *   La plupart des scripts utilitaires (ex: `generate_rhetorical_analysis_summaries.py`, `check_imports.py`) sont stables et peuvent être utilisés pour des tâches de développement et de maintenance.
    *   Les scripts de test basés sur les mocks (voir section 3) sont fiables.
*   **`tests/mocks/` (Mocks JPype et autres) :**
    *   Les mocks pour JPype et d'autres bibliothèques (NumPy, Pandas, Matplotlib, etc.) sont stables et permettent le développement et les tests des composants Python sans dépendance Java.
    *   Les tests unitaires utilisant ces mocks sont la base de la validation des fonctionnalités Python.
*   **Workflow d'Analyse Python Complet (Tâche 1.3b) :**
    *   Un script dédié, [`scripts/run_full_python_analysis_workflow.py`](scripts/run_full_python_analysis_workflow.py:1), permet d'exécuter un pipeline d'analyse complet en utilisant uniquement des composants Python.
    *   Ce workflow inclut :
        *   La dérivation de clé de chiffrement et le chargement d'un corpus chiffré (ex: [`tests/extract_sources_with_full_text.enc`](tests/extract_sources_with_full_text.enc)).
        *   L'extraction du contenu textuel (`full_text`).
        *   L'utilisation de `InformalAgent` avec un `MockFallacyDetector` pour simuler l'analyse rhétorique sans dépendance LLM ou Java.
        *   La génération de rapports d'analyse structurés aux formats JSON ([`results/full_python_analysis_report.json`](results/full_python_analysis_report.json:1)) et Markdown ([`results/full_python_analysis_report.md`](results/full_python_analysis_report.md:1)).
    *   Ce workflow est couvert par des tests fonctionnels dans [`tests/functional/test_python_analysis_workflow_components.py`](tests/functional/test_python_analysis_workflow_components.py:1), qui vérifient son exécution de bout en bout et la validité des rapports générés.
    *   **Statut :** Stable et validé pour l'analyse Python pure.

## 2. Problèmes Connus et Limitations Actuelles

L'intégration réelle avec JPype et la bibliothèque Java Tweety est le principal point de développement et de stabilisation en cours.

*   **Intégration JPype/Tweety Réelle :**
    *   L'intégration directe avec la JVM et la bibliothèque Tweety (via `jpype_tweety` dans `tests/integration/jpype_tweety/`) est **en cours de stabilisation**.
    *   Des problèmes de `CLASSPATH`, de chargement de classes Java (`ClassNotFoundException`, `NoClassDefFoundError`), et de compatibilité de version JVM/JPype peuvent encore survenir.
    *   Les tests marqués avec `@pytest.mark.real_jpype` ou situés dans `tests/integration/jpype_tweety/` nécessitent une JVM correctement configurée et peuvent échouer si l'environnement n'est pas parfait.
*   **Dépendance à la JVM :**
    *   Les fonctionnalités qui nécessitent une interaction directe avec Tweety (par exemple, la logique d'argumentation avancée, les opérations sur les théories) ne sont pas encore pleinement utilisables sans une configuration JVM stable.
    *   Les performances de l'intégration JPype peuvent varier et sont un sujet d'optimisation future.

## 3. Lancement des Tests Unitaires (Basés sur les Mocks)

Pour lancer les tests unitaires qui valident les fonctionnalités Python stables et qui utilisent intensivement les mocks (ne nécessitant pas de JVM réelle), suivez ces étapes :

1.  **Activez votre environnement virtuel Python :**
    *   Sur Windows (PowerShell) : `.\venv\Scripts\Activate.ps1`
    *   Sur macOS / Linux : `source venv/bin/activate`

2.  **Installez les dépendances (si ce n'est pas déjà fait) :**
    ```powershell
    pip install -r requirements.txt
    ```

3.  **Lancez Pytest en excluant les tests d'intégration réels :**
    Pour exécuter uniquement les tests unitaires et ceux basés sur les mocks, vous pouvez utiliser la commande `pytest` en excluant les marqueurs spécifiques aux tests réels.

    ```powershell
    pytest -m "not real_jpype"
    ```
    *Note :* Si vous n'avez pas de marqueur `real_jpype` configuré, vous pouvez simplement exécuter `pytest` et les tests qui échouent sans JVM seront identifiables par leurs erreurs. Il est recommandé de configurer ce marqueur dans `pytest.ini` ou `pyproject.toml`.

    Alternativement, vous pouvez cibler des répertoires spécifiques de tests unitaires, par exemple :
    ```powershell
    pytest tests/unit/ tests/mocks/
    ```
    (Cette commande suppose une future réorganisation des tests comme proposé dans `docs/PROPOSITION_REORG_TESTS.md`).

## 4. Tests d'Intégration Réels (`@pytest.mark.real_jpype`)

Les tests d'intégration qui nécessitent une JVM réelle et l'intégration Tweety sont en cours de stabilisation. Pour les exécuter, vous devez d'abord vous assurer que votre environnement Java (JDK 17, `JAVA_HOME`, `PATH`, `CLASSPATH` si nécessaire) est parfaitement configuré comme décrit dans le [`GUIDE_INSTALLATION_ETUDIANTS.md`](GUIDE_INSTALLATION_ETUDIANTS.md:1).

Une fois votre environnement Java prêt, vous pouvez tenter de lancer ces tests avec :

```powershell
pytest -m real_jpype
```
Soyez conscient que ces tests sont plus susceptibles de rencontrer des problèmes liés à l'environnement.