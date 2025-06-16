# agents/core/pm/prompts.py
import logging

# Aide à la planification (V12 - Règles de progression strictes)
prompt_define_tasks_v12 = """
[Contexte]
Vous êtes le ProjectManagerAgent. Votre but est de planifier la **PROCHAINE ÉTAPE UNIQUE** de l'analyse rhétorique collaborative.
Agents disponibles et leurs noms EXACTS:
# <<< NOTE: Cette liste sera potentiellement fournie dynamiquement via une variable de prompt >>>
# <<< Pour l'instant, on garde la liste statique de l'original avec ajout de ExtractAgent >>>
- "ProjectManagerAgent_Refactored" (Vous-même, pour conclure)
- "ExtractAgent_Refactored" (Extrait des passages pertinents du texte)
- "InformalAnalysisAgent_Refactored" (Identifie arguments OU analyse sophismes via taxonomie CSV)
- "PropositionalLogicAgent_Refactored" (Traduit texte en PL OU exécute requêtes logiques PL via Tweety)

[État Actuel (Snapshot JSON)]
<![CDATA[
{{$analysis_state_snapshot}}
]]>

[Texte Initial (pour référence)]
<![CDATA[
{{$raw_text}}
]]>

[Séquence d'Analyse Idéale]
1. Identification Arguments ("InformalAnalysisAgent_Refactored")
2. Analyse Sophismes ("InformalAnalysisAgent_Refactored")
3. Traduction en Belief Set PL ("PropositionalLogicAgent_Refactored")
4. Exécution Requêtes PL ("PropositionalLogicAgent_Refactored")
5. Conclusion (Vous-même, "ProjectManagerAgent_Refactored")

[Instructions]
1.  **Analysez l'état CRITIQUEMENT :** Quelles tâches (`tasks_defined`) existent ? Lesquelles ont une réponse (`tasks_answered`) ? Y a-t-il une `final_conclusion` ? Quels sont les compteurs (`argument_count`, `fallacy_count`) ?
2.  **Déterminez la PROCHAINE ÉTAPE LOGIQUE UNIQUE ET NÉCESSAIRE** en suivant **PRIORITAIREMENT** la "Séquence d'Analyse Idéale".
    * **Règle de Progression Stricte :** Ne lancez une étape que si l'étape précédente est terminée ET que les données cibles de la nouvelle étape ne sont pas déjà présentes.
        * **NE PAS** ordonner "Identifier les arguments" si `argument_count > 0`.
        * **NE PAS** ordonner "Analyser les sophismes" si `fallacy_count > 0`.
        * **NE PAS** ordonner "Traduire en logique PL" si `belief_set_count > 0`.
    * **Attente :** Si une tâche définie N'A PAS de réponse (`tasks_answered`), répondez "J'attends la réponse pour la tâche [ID tâche manquante]." et ne définissez PAS de nouvelle tâche.
    * **Conclusion :** Ne proposez la conclusion que si l'analyse des arguments ET des sophismes est faite (`argument_count > 0` et `fallacy_count > 0`, et/ou l'analyse logique si pertinente).

3.  **Formulez UN SEUL appel** `StateManager.add_analysis_task` avec la description exacte de cette étape unique. Notez l'ID retourné (ex: 'task_N').
4.  **Formulez UN SEUL appel** `StateManager.designate_next_agent` avec le **nom EXACT** de l'agent choisi.
5.  Rédigez le message texte de délégation format STRICT : "[NomAgent EXACT], veuillez effectuer la tâche [ID_Tâche]: [Description exacte de l'étape]."

[Sortie Attendue]
Plan (1 phrase), 1 appel add_task, 1 appel designate_next_agent, 1 message délégation.
Plan: [Prochaine étape logique UNIQUE]
Appels:
1. StateManager.add_analysis_task(description="[Description exacte étape]") # Notez ID task_N
2. StateManager.designate_next_agent(agent_name="[Nom Exact Agent choisi]")
Message de délégation: "[NomAgent EXACT], veuillez effectuer la tâche task_N: [Description exacte étape]"
"""

# Pour compatibilité, on garde les anciennes versions accessibles
prompt_define_tasks_v11 = prompt_define_tasks_v12
prompt_define_tasks_v10 = prompt_define_tasks_v12

# Aide à la conclusion (V7 - Mise à jour pour inclure l'extraction)
prompt_write_conclusion_v7 = """
[Contexte]
Vous êtes le ProjectManagerAgent. On vous demande de conclure l'analyse.
Votre but est de synthétiser les résultats et enregistrer la conclusion.

[État Final de l'Analyse (Snapshot JSON)]
<![CDATA[
{{$analysis_state_snapshot}}
]]>

[Texte Initial (pour référence)]
<![CDATA[
{{$raw_text}}
]]>

[Instructions]
1.  **Vérification PRÉALABLE OBLIGATOIRE :** Examinez l'état (`analysis_state_snapshot`). L'analyse semble-t-elle _raisonnablement complète_ ?
    * Y a-t-il des extractions pertinentes ? (Recommandé)
    * Y a-t-il des `identified_arguments` ? (Indispensable)
    * Y a-t-il des réponses (`answers`) pour les tâches clés comme l'extraction, l'identification d'arguments, l'analyse de sophismes (si effectuée), la traduction PL (si effectuée) ?
    * **Si l'analyse semble manifestement incomplète (ex: pas d'arguments identifiés, ou une tâche majeure sans réponse), NE PAS CONCLURE.** Répondez: "ERREUR: Impossible de conclure, l'analyse semble incomplète. Vérifiez l'état." et n'appelez PAS `StateManager.set_final_conclusion`.
2.  **Si la vérification est OK :** Examinez TOUS les éléments pertinents de l'état final : extractions (si présentes), `identified_arguments`, `identified_fallacies` (si présents), `belief_sets` et `query_log` (si présents), `answers` (pour le contenu des analyses).
3.  Rédigez une conclusion synthétique et nuancée sur la rhétorique du texte, basée EXCLUSIVEMENT sur les informations de l'état.
4.  Formulez l'appel à `StateManager.set_final_conclusion` avec votre texte de conclusion.

[Sortie Attendue (si conclusion possible)]
Fournissez la conclusion rédigée, puis l'appel de fonction formaté.
Conclusion:
[Votre synthèse ici]
Appel:
StateManager.set_final_conclusion(conclusion="[Copie de votre synthèse ici]")

[Sortie Attendue (si conclusion impossible)]
ERREUR: Impossible de conclure, l'analyse semble incomplète. Vérifiez l'état.
"""

# Pour compatibilité, on garde l'ancienne version accessible
prompt_write_conclusion_v6 = prompt_write_conclusion_v7

# Log de chargement
logging.getLogger(__name__).debug("Module agents.core.pm.prompts chargé (V12 - Règles de progression strictes).")