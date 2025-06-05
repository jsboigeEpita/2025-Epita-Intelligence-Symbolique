# examples/cluedo_demo/demo_cluedo_workflow.py

import json # Ajouté pour parser le JSON dans le texte des hypothèses
import asyncio
from unittest.mock import AsyncMock, MagicMock # Pour mocker les appels LLM

# Adapter les imports selon la structure réelle du projet
from argumentation_analysis.core.enquete_states import EnqueteCluedoState
# SolutionCluedo n'est pas une classe mais un dict, géré dans EnqueteCluedoState
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.orchestration.cluedo_orchestrator import CluedoGroupChatManager

from semantic_kernel.agents import Agent # semantic_kernel.agents.agent est la nouvelle convention
from semantic_kernel.agents import GroupChatOrchestration # Utiliser GroupChatOrchestration
from semantic_kernel.agents import RoundRobinGroupChatManager # Correction: Importer depuis semantic_kernel.agents
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion # Ou AzureChatCompletion

# --- Configuration Globale et Mocks ---
print("--- Début de la Démonstration du Workflow Cluedo ---")

# Mock du Kernel et des services LLM pour éviter les appels réels
mock_kernel = MagicMock(spec=Kernel) # Utiliser MagicMock pour permettre l'assignation de .invoke
mock_chat_service = MagicMock(spec=OpenAIChatCompletion) 

# Pour SK Python v0.9.3b1 et plus récent, kernel.invoke est utilisé.
# Les agents SK utilisent typiquement kernel.invoke_prompt ou des fonctions sémantiques.
# Pour la démo, on mock la méthode invoke du kernel qui est souvent le point central.
# La valeur retournée doit être un FunctionResult ou un objet similaire que les agents attendent.
# Un simple MagicMock(value="...") est souvent suffisant pour simuler la sortie d'une fonction sémantique.
mock_kernel.invoke = AsyncMock(return_value=MagicMock(value="Réponse mockée du LLM"))

# Configurer mock_kernel.plugins pour simuler un KernelPluginCollection
_plugin_storage = {} # Stockage pour nos instances de plugin mockées

def _mock_add_plugin_side_effect(plugin_instance, plugin_name):
    _plugin_storage[plugin_name] = plugin_instance
    # La vraie méthode add_plugin retourne la collection de plugins elle-même
    return mock_kernel.plugins

def _mock_get_plugin_side_effect(plugin_name_to_get):
    return _plugin_storage.get(plugin_name_to_get)

mock_kernel.plugins = MagicMock()
mock_kernel.add_plugin = MagicMock(side_effect=_mock_add_plugin_side_effect)
mock_kernel.plugins.get = MagicMock(side_effect=_mock_get_plugin_side_effect)

# Rendre mock_kernel.invoke plus intelligent pour appeler les vraies fonctions du plugin mocké
async def _mock_kernel_invoke_side_effect(*args, **kwargs):
    plugin_name = kwargs.get("plugin_name")
    function_name = kwargs.get("function_name")
    
    # Retirer les arguments spécifiques à invoke pour ne passer que ceux de la fonction
    kernel_args_dict = {k: v for k, v in kwargs.items() if k not in ["plugin_name", "function_name", "kernel"]}

    if plugin_name and function_name:
        plugin_instance = _plugin_storage.get(plugin_name)
        if plugin_instance and hasattr(plugin_instance, function_name):
            method_to_call = getattr(plugin_instance, function_name)
            
            # Les fonctions Kernel attendent souvent des arguments spécifiques ou un KernelArguments
            # Pour la démo, on passe directement les kwargs restants.
            # Une vraie fonction kernel pourrait retourner un FunctionResult.
            # Ici, on retourne la valeur directement si la fonction du plugin la retourne,
            # ou un mock si la fonction retourne un objet complexe.
            try:
                # Supposer que les fonctions du plugin retournent des valeurs sérialisables en JSON (str)
                # ou des objets simples. Le plugin actuel retourne des str JSON.
                result_val = method_to_call(**kernel_args_dict)
                # Simuler un FunctionResult simple
                mock_function_result = MagicMock()
                mock_function_result.value = result_val # Le plugin retourne déjà du JSON str
                return mock_function_result
            except Exception as e:
                print(f"Erreur lors de l'appel mocké à {plugin_name}.{function_name}: {e}")
                mock_error_result = MagicMock()
                mock_error_result.value = json.dumps({"error": str(e)})
                return mock_error_result
    
    # Fallback si le plugin/fonction n'est pas géré par ce mock avancé
    print(f"Fallback: mock_kernel.invoke appelé avec plugin='{plugin_name}', function='{function_name}' non géré dynamiquement, retournant mock par défaut.")
    mock_default_result = MagicMock()
    mock_default_result.value = "Réponse mockée du LLM (fallback)"
    return mock_default_result

mock_kernel.invoke = AsyncMock(side_effect=_mock_kernel_invoke_side_effect)
# Si les agents utilisent directement get_chat_message_contents (moins courant pour les agents SK standards)
# mock_chat_service.get_chat_message_contents = AsyncMock(return_value=[MagicMock(content="Réponse mockée du LLM")])


# --- Niveau 1: Illustrations Unitaires ---
print("\n--- Niveau 1: Illustrations Unitaires des Composants ---")

# 1.1 EnqueteCluedoState
print("\n# 1.1 EnqueteCluedoState")
# Définition des éléments du jeu
PERSONNAGES_LIST = ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"]
ARMES_LIST = ["Poignard", "Revolver", "Corde"]
LIEUX_LIST = ["Cuisine", "Salon", "Bureau"]

ELEMENTS_JEU_CLUEDO = {
    "suspects": PERSONNAGES_LIST,
    "armes": ARMES_LIST,
    "lieux": LIEUX_LIST
}
NOM_ENQUETE_DEMO = "Mystère au Manoir Mock"
DESCRIPTION_CAS_DEMO = "Un meurtre a été commis, il faut trouver le coupable, l'arme et le lieu."
INITIAL_CONTEXT_DEMO = {"source": "Démo Cluedo"}


print("Création d'un état d'enquête avec solution auto-générée:")
try:
    etat_enquete_auto = EnqueteCluedoState(
        nom_enquete_cluedo=NOM_ENQUETE_DEMO,
        elements_jeu_cluedo=ELEMENTS_JEU_CLUEDO,
        description_cas=DESCRIPTION_CAS_DEMO,
        initial_context=INITIAL_CONTEXT_DEMO,
        auto_generate_solution=True
    )
    print(f"État créé. Solution générée: {etat_enquete_auto.solution_secrete_cluedo}")
    # Hypotheses_emises n'est pas un attribut direct de EnqueteCluedoState, 
    # mais de EnquetePoliciereState (sa classe parente) sous `hypotheses_enquete`
    print(f"Hypothèses initiales (via classe parente): {etat_enquete_auto.hypotheses_enquete}")
except Exception as e:
    print(f"Erreur lors de la création de l'état auto-généré: {e}")
    etat_enquete_auto = None

print("\nCréation d'un état d'enquête avec solution prédéfinie:")
# SolutionCluedo est un dict
solution_predefinie_dict = {"suspect": "Professeur Violet", "arme": "Revolver", "lieu": "Bureau"}
try:
    etat_enquete_defini = EnqueteCluedoState(
        nom_enquete_cluedo=NOM_ENQUETE_DEMO + " (défini)",
        elements_jeu_cluedo=ELEMENTS_JEU_CLUEDO,
        description_cas=DESCRIPTION_CAS_DEMO,
        initial_context=INITIAL_CONTEXT_DEMO,
        solution_secrete_cluedo=solution_predefinie_dict,
        auto_generate_solution=False # Important
    )
    print(f"État créé. Solution définie: {etat_enquete_defini.solution_secrete_cluedo}")

    if etat_enquete_defini:
        print("Ajout d'une hypothèse à l'état (via méthode de la classe parente):")
        # La méthode add_hypothesis de EnquetePoliciereState attend text, confidence_score
        # Le plan suggère ajouter_hypothese("Colonel Moutarde", "Poignard", "Cuisine", "Sherlock")
        # Cela ne correspond pas à la signature. On va adapter.
        # EnqueteCluedoState a une méthode `ajouter_hypothese_cluedo`
        if hasattr(etat_enquete_defini, "ajouter_hypothese_cluedo"):
            etat_enquete_defini.ajouter_hypothese_cluedo(
                auteur="Sherlock",
                suspect="Colonel Moutarde",
                arme="Poignard",
                lieu="Cuisine",
                type_raisonnement="Déduction initiale"
            )
            print(f"Hypothèses après ajout (spécifique Cluedo): {etat_enquete_defini.hypotheses_enquete}") # Correction: hypotheses_cluedo -> hypotheses_enquete
        else: # Fallback sur la méthode générique si l'autre n'existe pas
            etat_enquete_defini.add_hypothesis(
                text="Hypothèse: Colonel Moutarde avec le Poignard dans la Cuisine",
                confidence_score=0.7,
                # hypothesis_id est généré automatiquement
            )
            print(f"Hypothèses après ajout (générique): {etat_enquete_defini.hypotheses_enquete}")

        print("Ajout d'une carte révélée à un joueur (Watson voit 'Corde'):")
        # Note pour la démo: Les méthodes spécifiques à la gestion des cartes des joueurs (ajouter_carte_montree_joueur, get_cartes_joueur)
        # ne sont pas implémentées dans la version actuelle de EnqueteCluedoState.
        print("Note Démo: La gestion des cartes spécifiques aux joueurs (ex: ajouter_carte_montree_joueur) n'est pas implémentée dans EnqueteCluedoState.")
        # if hasattr(etat_enquete_defini, "ajouter_carte_montree_joueur"):
        #     etat_enquete_defini.ajouter_carte_montree_joueur(nom_joueur="Watson", carte="Corde", source_info="Observation directe")
        #     if hasattr(etat_enquete_defini, "get_cartes_joueur"):
        #          print(f"Cartes connues de Watson: {etat_enquete_defini.get_cartes_joueur('Watson')}")
        #     else:
        #          print(f"Cartes de Watson (accès direct si pas de getter): {etat_enquete_defini.cartes_connues_joueurs.get('Watson') if hasattr(etat_enquete_defini, 'cartes_connues_joueurs') else 'Attribut cartes_connues_joueurs non trouvé'}")
        # else:
        #     print("Méthode pour ajouter/voir carte joueur non trouvée comme prévu (confirmé).")

except Exception as e:
    print(f"Erreur lors de la création ou manipulation de l'état défini: {e}")
    etat_enquete_defini = None


# 1.2 Agents (SherlockEnqueteAgent, WatsonLogicAssistant)
print("\n# 1.2 Agents (Sherlock & Watson)")

print("\nInstanciation de SherlockEnqueteAgent:")
try:
    # SherlockEnqueteAgent hérite de ProjectManagerAgent. Vérifier son constructeur.
    # ProjectManagerAgent(kernel, agent_name, instructions, description, plugin_name)
    sherlock = SherlockEnqueteAgent(
        kernel=mock_kernel,
        agent_name="Sherlock Holmes",
        system_prompt="Vous êtes Sherlock Holmes, un détective de renommée mondiale. Votre mission est de résoudre ce Cluedo.", # Correction: instructions -> system_prompt
        # description est optionnel dans ProjectManagerAgent, plugin_name aussi
    )
    print(f"Sherlock instancié: {sherlock.name}") # ProjectManagerAgent a un attribut `name`
except Exception as e:
    print(f"Erreur lors de l'instanciation de Sherlock: {e}")
    sherlock = None

print("\nInstanciation de WatsonLogicAssistant:")
try:
    # WatsonLogicAssistant hérite de PropositionalLogicAgent. Vérifier son constructeur.
    # PropositionalLogicAgent(kernel, agent_name, instructions, description, plugin_name, belief_set_id)
    watson = WatsonLogicAssistant(
        kernel=mock_kernel,
        agent_name="Dr. Watson",
        system_prompt="Vous êtes Dr. Watson, l'assistant logique de Sherlock. Analysez les faits et déductions.", # Correction: instructions -> system_prompt
        # belief_set_id est important pour les agents logiques.
        # On peut le lier à l'état de l'enquête si nécessaire, ou utiliser un mock.
        # belief_set_id="watson_cluedo_bs_demo" # Retiré, car non attendu par le constructeur
    )
    print(f"Watson instancié: {watson.name}")
    # Note: belief_set_id pourrait devoir être configuré autrement, par ex. via une méthode ou un plugin.
except Exception as e:
    print(f"Erreur lors de l'instanciation de Watson: {e}")
    watson = None

# 1.3 EnqueteStateManagerPlugin
print("\n# 1.3 EnqueteStateManagerPlugin")
try:
    if etat_enquete_defini:
        # Le plugin prend l'état en argument de son constructeur
        plugin_etat = EnqueteStateManagerPlugin(etat_enquete_defini)
        print("Plugin EnqueteStateManagerPlugin instancié.")

        mock_kernel.add_plugin(plugin_etat, plugin_name="EnqueteManager")
        print("Plugin ajouté au mock_kernel sous le nom 'EnqueteManager'.")

        # Test d'une fonction du plugin.
        # Le plan suggère get_etat_actuel_formate ou obtenir_contexte_enquete
        # EnqueteStateManagerPlugin a `get_info_etat_actuel` et `get_hypotheses_formatees` etc.
        if hasattr(plugin_etat, "get_info_etat_actuel"):
            resume_etat = plugin_etat.get_info_etat_actuel() # C'est une méthode @kernel_function
            # Pour l'appeler directement, il faut simuler l'appel du kernel ou appeler la méthode sous-jacente
            # Pour la démo, on peut essayer d'appeler la méthode python directement si elle n'est pas async.
            # Si elle est async, il faut un await.
            # Si c'est une @kernel_function, elle est appelée via kernel.invoke
            # Remplacer par get_hypotheses car get_info_etat_actuel n'existe pas
            print("Tentative d'appel à get_hypotheses via kernel.invoke (mocké):")
            async def demo_plugin_call():
                result = await mock_kernel.invoke(plugin_name="EnqueteManager", function_name="get_hypotheses")
                print(f"Hypothèses via le plugin (invoke mocké): {str(result.value)[:200]}...")
            asyncio.run(demo_plugin_call())
        # else: # Commenté car on tente get_hypotheses
            # print("Méthode get_info_etat_actuel non trouvée sur le plugin pour la démo.")
    else:
        print("État d'enquête non disponible, skip démo plugin.")
        plugin_etat = None
except Exception as e:
    print(f"Erreur avec EnqueteStateManagerPlugin: {e}")
    plugin_etat = None


# --- Niveau 2: Illustrations d'Intégration ---
print("\n--- Niveau 2: Illustrations d'Intégration des Composants ---")

if sherlock and watson and plugin_etat and etat_enquete_defini and mock_kernel.plugins.get("EnqueteManager"):
    print("\n# 2.1 Interaction Sherlock -> Plugin Etat -> Watson")

    async def sherlock_makes_hypothesis_demo_integration():
        print("\nSherlock (simulé) formule une hypothèse via le plugin...")
        try:
            # Sherlock utiliserait kernel.invoke("EnqueteManager", "enregistrer_hypothese_cluedo_agent", ...)
            # La fonction du plugin est `enregistrer_hypothese_cluedo_agent`
            # Elle prend: agent_name, suspect, arme, lieu, type_raisonnement, notes_optionnelles
            # Utiliser add_hypothesis car enregistrer_hypothese_cluedo_agent n'est pas une fonction standard du plugin
            texte_hypothese_sherlock_section2 = f"Hypothèse de {sherlock.name} (Section 2.1): {{\"suspect\": \"Colonel Moutarde\", \"arme\": \"Poignard\", \"lieu\": \"Cuisine\"}}. Raison: Intuition initiale. Notes: Je le sens bien."
            await mock_kernel.invoke(
                plugin_name="EnqueteManager",
                function_name="add_hypothesis", # Correction
                text=texte_hypothese_sherlock_section2,
                confidence_score=0.75
            )
            print(f"Hypothèse de Sherlock enregistrée. État actuel des hypothèses Cluedo: {etat_enquete_defini.hypotheses_enquete}")
        except Exception as e:
            print(f"Erreur lors de la simulation de l'hypothèse de Sherlock (intégration): {e}")

    asyncio.run(sherlock_makes_hypothesis_demo_integration())

    async def watson_analyzes_state_demo_integration():
        print("\nWatson (simulé) analyse l'état actuel via le plugin...")
        try:
            # Watson pourrait demander les hypothèses ou l'état général
            # Par exemple, `get_hypotheses_formatees`
            print("Watson (via appel mocké au kernel) -> EnqueteManager.get_hypotheses_formatees")
            result_hypotheses = await mock_kernel.invoke(plugin_name="EnqueteManager", function_name="get_hypotheses") # Correction: get_hypotheses_formatees -> get_hypotheses
            contexte_pour_watson = result_hypotheses.value
            print(f"Watson reçoit les hypothèses formatées (mocké): {str(contexte_pour_watson)[:150]}...")

            # Logique de Watson (très simplifiée)
            # La gestion des cartes par joueur n'étant pas dans EnqueteCluedoState, cette section est simplifiée.
            print("Watson analyse: (Simulation) L'hypothèse de Sherlock est notée.")
            
            derniere_hypothese = etat_enquete_defini.hypotheses_enquete[-1] if etat_enquete_defini.hypotheses_enquete else None
            if derniere_hypothese:
                print(f"Watson prend note de l'hypothèse: {derniere_hypothese.get('text')}")
            # else: # Ce else correspondait à la ligne 273 problématique.
                # print("Watson analyse: Pas d'hypothèse claire à analyser ou la logique des cartes est absente.")

        except Exception as e:
            print(f"Erreur lors de la simulation de l'analyse de Watson (intégration): {e}")

    asyncio.run(watson_analyzes_state_demo_integration())

else:
    print("\nUn ou plusieurs composants (Sherlock, Watson, PluginEtat, EtatEnquete) n'ont pas pu être initialisés. Skip Niveau 2 Intégration.")


# --- Niveau 2.2: Orchestration avec GroupChat (si les composants sont prêts) ---
print("\n# 2.2 Orchestration de base avec GroupChat")
if sherlock and watson and plugin_etat and etat_enquete_defini and mock_kernel.plugins.get("EnqueteManager"):
    print("Configuration du GroupChat...")
    try:
        # CluedoGroupChatManager hérite de RoundRobinGroupChatManager
        # Son constructeur est CluedoGroupChatManager(members, enquete_state_plugin, kernel, name, max_consecutive_utterances)
        cluedo_chat_manager = CluedoGroupChatManager(
            members=[sherlock, watson],
            enquete_state_plugin=plugin_etat, # Il attend le plugin, pas l'état directement
            kernel=mock_kernel,
            # name="CluedoChatManagerDemo" # Optionnel
            # max_consecutive_utterances est optionnel
        )
        print("CluedoGroupChatManager instancié.")

        # GroupChat(members, manager, runtime=None)
        # Le runtime InProcessRuntime n'est plus nécessaire/utilisé de la même manière dans les versions récentes de SK.
        # Les agents sont directement appelables.
        group_chat = GroupChatOrchestration( # Utiliser GroupChatOrchestration
            members=[sherlock, watson], # Correction: GroupChatOrchestration attend probablement 'members'
            manager=cluedo_chat_manager,
        )
        print("GroupChatOrchestration instancié.")

        print("\nSimulation d'une brève interaction dans GroupChat (1-2 tours):")
        
        # Mocker les réponses successives de kernel.invoke pour simuler un dialogue.
        # C'est la partie la plus délicate.
        # Le manager (CluedoGroupChatManager) a une logique pour sélectionner le prochain agent
        # et potentiellement pour terminer le chat (is_complete).
        
        # Pour la démo, on va se contenter d'illustrer le principe sans exécuter un chat complet,
        # car cela nécessiterait de mocker finement les `invoke` des agents et la logique du manager.
        
        async def chat_turn_simulation_principle():
            print("Principe de fonctionnement du GroupChat:")
            print("1. Le GroupChat reçoit un message initial (ex: 'Commençons l'enquête').")
            print("2. Le CluedoGroupChatManager sélectionne un agent (ex: Sherlock via round-robin).")
            print("3. L'agent sélectionné (Sherlock) est invoqué. Son `invoke` (mocké ici) utilise `mock_kernel.invoke`.")
            print("   - `mock_kernel.invoke` retourne 'Réponse mockée du LLM' ou une valeur configurée.")
            print("   - Sherlock pourrait aussi utiliser le plugin EnqueteManager via `kernel.invoke(...)`.")
            print("4. La réponse de Sherlock est ajoutée à l'historique du chat.")
            print("5. Le manager vérifie si la discussion est terminée (via sa méthode `is_complete`).")
            print("   - Pour la démo, on supposerait que `is_complete` retourne False initialement.")
            print("6. Le manager sélectionne l'agent suivant (ex: Watson).")
            print("7. Watson est invoqué, sa réponse (mockée) est ajoutée.")
            print("8. Le cycle continue jusqu'à ce que `is_complete` du manager retourne True.")
            
            # Exemple de simulation d'un seul tour si on voulait aller plus loin (complexe à bien mocker)
            # On pourrait surcharger mock_kernel.invoke pour qu'il retourne des choses différentes
            # en fonction de qui l'appelle ou du nombre d'appels.
            
            # mock_kernel.invoke = AsyncMock(side_effect=[
            #     MagicMock(value="Sherlock: Je pense que c'est Moutarde avec le Poignard dans la Cuisine."),
            #     MagicMock(value="Watson: Intéressant, mais j'ai la carte Poignard.")
            # ])
            #
            # # Mocker is_complete du manager pour qu'il s'arrête après quelques tours
            # cluedo_chat_manager.is_complete = MagicMock(side_effect=[False, False, True]) # 2 messages puis stop
            #
            # try:
            #     initial_prompt = "Début de l'enquête Cluedo."
            #     final_history = await group_chat.invoke(input=initial_prompt) # L'input est une liste de messages ou un str
            #     print("\nHistorique du chat simulé (très mocké):")
            #     for message in final_history: # La structure de message dépend de l'agent
            #         # Pour les agents SK standards, c'est souvent un ChatMessageContent
            #         actor_name = message.name if hasattr(message, 'name') else message.author_name # ou agent_name
            #         print(f"- {actor_name}: {message.content}")
            # except Exception as chat_ex:
            #     print(f"Erreur détaillée pendant la simulation (très mockée) du chat: {type(chat_ex).__name__}: {chat_ex}")
            # finally:
            #      # Restaurer le mock simple pour les tests suivants
            #     mock_kernel.invoke = AsyncMock(return_value=MagicMock(value="Réponse mockée du LLM"))
            #     if hasattr(cluedo_chat_manager, 'is_complete') and isinstance(cluedo_chat_manager.is_complete, MagicMock):
            #         cluedo_chat_manager.is_complete.side_effect = None


            print("\nLa simulation d'un chat interactif complet est complexe à mocker de manière concise.")
            print("L'objectif principal ici est de montrer que GroupChat et CluedoGroupChatManager peuvent être instanciés avec les agents et plugins mockés.")

        asyncio.run(chat_turn_simulation_principle())

    except Exception as e:
        print(f"Erreur lors de la configuration ou simulation du GroupChat: {e}")
else:
    print("\nUn ou plusieurs composants nécessaires pour le GroupChat ne sont pas prêts. Skip démo GroupChat.")


# --- Niveau 3: Illustration Fonctionnelle (Optionnel et Simplifié) ---
print("\n--- Niveau 3: Illustration Fonctionnelle (Très Simplifié) ---")

if etat_enquete_defini and sherlock and watson and plugin_etat and mock_kernel.plugins.get("EnqueteManager"):
    print("\nScénario fonctionnel simplifié:")
    print(f"Solution secrète pour ce scénario: {etat_enquete_defini.solution_secrete_cluedo}")
    
    # Réinitialisation partielle de l'état pour ce scénario
    if hasattr(etat_enquete_defini, 'hypotheses_enquete'): # Correction
        etat_enquete_defini.hypotheses_enquete = [] # Correction
    if hasattr(etat_enquete_defini, 'cartes_connues_joueurs'):
        etat_enquete_defini.cartes_connues_joueurs = {}
    
    async def functional_flow_demo_simplified(solution_definie_scenario: dict):
        try:
            # 1. Sherlock fait une hypothèse (Moutarde, Corde, Salon)
            print("\nÉtape 1: Sherlock fait une hypothèse (Moutarde, Corde, Salon).")
            # Utiliser add_hypothesis car enregistrer_hypothese_cluedo_agent n'est pas une fonction standard du plugin
            # et la structure de l'hypothèse doit correspondre à ce que add_hypothesis crée.
            # Pour la démo, nous allons construire le texte de l'hypothèse.
            texte_hypothese_sherlock = f"Hypothèse de {sherlock.name}: {{\"suspect\": \"Colonel Moutarde\", \"arme\": \"Corde\", \"lieu\": \"Salon\"}}. Raison: Déduction initiale scénario 3"
            await mock_kernel.invoke(
                plugin_name="EnqueteManager",
                function_name="add_hypothesis", # Correction: utiliser add_hypothesis
                text=texte_hypothese_sherlock,
                confidence_score=0.8
                # Les arguments agent_name, suspect, arme, lieu ne sont pas pris par add_hypothesis directement.
                # Ils doivent être inclus dans le 'text' ou gérés par une fonction plugin plus spécifique si elle existait.
            )
            # Récupérer l'hypothèse APRÈS son enregistrement
            derniere_hypothese_objet = etat_enquete_defini.hypotheses_enquete[-1] if etat_enquete_defini.hypotheses_enquete else {}
            texte_derniere_hypothese = derniere_hypothese_objet.get("text", "")
            
            # Tentative de parsing simple du JSON embarqué dans le texte pour la démo
            solution_proposee_section3 = {"suspect": None, "arme": None, "lieu": None}
            try:
                # Chercher le JSON dans le texte, ex: '... {"suspect": "X", ...} ...'
                # Assurez-vous que json est importé au début du fichier: import json
                json_start = texte_derniere_hypothese.find('{')
                json_end = texte_derniere_hypothese.rfind('}') + 1
                if json_start != -1 and json_end != -1 and json_start < json_end:
                    json_str = texte_derniere_hypothese[json_start:json_end]
                    parsed_json = json.loads(json_str) # Nécessite import json
                    solution_proposee_section3["suspect"] = parsed_json.get("suspect")
                    solution_proposee_section3["arme"] = parsed_json.get("arme")
                    solution_proposee_section3["lieu"] = parsed_json.get("lieu")
            except Exception as parse_ex:
                print(f"Erreur de parsing JSON pour l'hypothèse: {parse_ex}")
                pass # Laisser les valeurs à None si le parsing échoue

            print(f"Hypothèse de Sherlock (après enregistrement, parsée): {solution_proposee_section3.get('suspect')}, {solution_proposee_section3.get('arme')}, {solution_proposee_section3.get('lieu')}.")
            # Remplacer hypothese_sherlock par solution_proposee_section3 pour la logique de comparaison plus bas
            # Cette variable sera utilisée dans la section 3 pour la comparaison avec la solution.
            # La variable `hypothese_sherlock` originale (l'objet dict complet) est dans `derniere_hypothese_objet`
            # Pour la comparaison de la solution, nous utilisons les éléments parsés.

            # 2. Information: Watson reçoit la carte "Corde".
            print("\nÉtape 2: Watson reçoit la carte 'Corde'.")
            if hasattr(etat_enquete_defini, "ajouter_carte_montree_joueur"):
                etat_enquete_defini.ajouter_carte_montree_joueur(watson.name, "Corde", "Distribution Scénario 3")
                cartes_watson = etat_enquete_defini.get_cartes_joueur(watson.name) if hasattr(etat_enquete_defini, "get_cartes_joueur") else []
                print(f"Cartes de Watson: {cartes_watson}")
            else:
                print("Impossible d'ajouter la carte à Watson.")


            # 3. Watson analyse et communique sa déduction.
            print("\nÉtape 3: Watson analyse et communique.")
            conclusion_watson = "Analyse non effectuée ou non concluante."
            if "Corde" in (cartes_watson if 'cartes_watson' in locals() else []):
                if hypothese_sherlock.get("arme") == "Corde":
                    conclusion_watson = f"L'arme 'Corde' de l'hypothèse de Sherlock est infirmée, car je possède cette carte."
                    # Watson enregistre sa déduction via le plugin
                    if hasattr(plugin_etat, "enregistrer_deduction_logique_agent"): # Fonction spécifique du plugin
                         await mock_kernel.invoke(
                            plugin_name="EnqueteManager", function_name="enregistrer_deduction_logique_agent",
                            agent_name=watson.name, deduction_text=conclusion_watson,
                            hypothese_cible_id=hypothese_sherlock.get("id_hypothese") # si l'ID est dispo
                        )
                    print(f"Watson conclut (mocké): {conclusion_watson}")
                else:
                    conclusion_watson = "Ma carte 'Corde' n'infirme pas l'arme de l'hypothèse actuelle de Sherlock."
                    print(f"Watson: {conclusion_watson}")
            else:
                conclusion_watson = "Watson: Je n'ai pas la carte 'Corde', ou mes cartes sont inconnues."
                print(conclusion_watson)

            # 4. Afficher les déductions (si le plugin le permet)
            if hasattr(plugin_etat, "get_deductions_logiques_formatees"):
                result_deductions = await mock_kernel.invoke(plugin_name="EnqueteManager", function_name="get_deductions_logiques_formatees")
                print(f"Déductions enregistrées (via plugin mocké): {str(result_deductions.value)[:200]}...")

            # Comparaison de la solution proposée avec la solution secrète
            # Assurer que solution_definie est accessible ici. Elle est définie au début du script.
            # Et solution_proposee_section3 est définie au début de cette fonction.
            print(f"\nComparaison de la solution pour le scénario simplifié:")
            print(f"Solution proposée (parsée de l'hypothèse de Sherlock): {solution_proposee_section3}")
            print(f"Solution secrète attendue: {solution_definie_scenario}")

            if solution_proposee_section3.get("suspect") == solution_definie_scenario.get("suspect") and \
               solution_proposee_section3.get("arme") == solution_definie_scenario.get("arme") and \
               solution_proposee_section3.get("lieu") == solution_definie_scenario.get("lieu") and \
               all(solution_proposee_section3.values()): # S'assurer qu'aucune valeur n'est None
                print("Bravo Sherlock! La solution proposée pour le scénario simplifié est correcte.")
            else:
                print("Dommage Sherlock. La solution proposée pour le scénario simplifié n'est pas la bonne, ou l'hypothèse n'a pas été correctement formulée/récupérée.")

        except Exception as e:
            print(f"Erreur dans le flux fonctionnel simplifié: {type(e).__name__} - {e}")

    asyncio.run(functional_flow_demo_simplified(etat_enquete_defini.solution_secrete_cluedo))
else:
    print("\nComposants manquants pour le flux fonctionnel simplifié.")


print("\n--- Fin de la Démonstration du Workflow Cluedo ---")