import uuid
import random
from typing import List, Dict, Any, Optional

class BaseWorkflowState:
    def __init__(self, initial_context: dict, workflow_id: str = None):
        self.workflow_id: str = workflow_id or str(uuid.uuid4())
        self.initial_context: dict = initial_context
        self.tasks: List[Dict] = [] # Voir Section 5 pour la structure
        self.results: List[Dict] = [] # Voir Section 5
        self.log_messages: List[Dict] = [] # {timestamp, agent_source, message_type, content}
        self.final_output: Dict = {} # Voir Section 5
        self._next_agent_designated: Optional[str] = None # Utilisé par l'orchestrateur

    # Méthodes pour les tâches
    def add_task(self, description: str, assignee: str, task_id: str = None) -> dict:
        # Placeholder implementation
        new_task = {
            "task_id": task_id or str(uuid.uuid4()),
            "description": description,
            "assignee": assignee,
            "status": "pending" # Example status
        }
        self.tasks.append(new_task)
        return new_task

    def get_task(self, task_id: str) -> Optional[dict]:
        # Placeholder implementation
        for task in self.tasks:
            if task["task_id"] == task_id:
                return task
        return None

    def update_task_status(self, task_id: str, status: str) -> bool:
        # Placeholder implementation
        task = self.get_task(task_id)
        if task:
            task["status"] = status
            return True
        return False

    def get_tasks(self, assignee: str = None, status: str = None) -> List[dict]:
        # Placeholder implementation
        filtered_tasks = self.tasks
        if assignee:
            filtered_tasks = [t for t in filtered_tasks if t.get("assignee") == assignee]
        if status:
            filtered_tasks = [t for t in filtered_tasks if t.get("status") == status]
        return filtered_tasks

    # Méthodes pour les résultats
    def add_result(self, query_id: str, agent_source: str, content: dict, result_id: str = None) -> dict:
        # Placeholder implementation
        new_result = {
            "result_id": result_id or str(uuid.uuid4()),
            "query_id": query_id,
            "agent_source": agent_source,
            "content": content
        }
        self.results.append(new_result)
        return new_result

    def get_results(self, query_id: str = None, agent_source: str = None) -> List[dict]:
        # Placeholder implementation
        filtered_results = self.results
        if query_id:
            filtered_results = [r for r in filtered_results if r.get("query_id") == query_id]
        if agent_source:
            filtered_results = [r for r in filtered_results if r.get("agent_source") == agent_source]
        return filtered_results

    # Méthodes pour les logs
    def add_log_message(self, agent_source: str, message_type: str, content: Any) -> None:
        # Placeholder implementation
        self.log_messages.append({
            "timestamp": str(uuid.uuid4()), # Using uuid for timestamp placeholder
            "agent_source": agent_source,
            "message_type": message_type,
            "content": content
        })

    # Méthode pour la sortie finale
    def set_final_output(self, output_data: dict) -> None:
        # Placeholder implementation
        self.final_output = output_data

    def get_final_output(self) -> dict:
        # Placeholder implementation
        return self.final_output

    # Gestion du prochain agent (pour l'orchestrateur)
    def designate_next_agent(self, agent_name: str) -> None:
        # Placeholder implementation
        self._next_agent_designated = agent_name

    def get_designated_next_agent(self) -> Optional[str]:
        # Placeholder implementation
        return self._next_agent_designated

class EnquetePoliciereState(BaseWorkflowState):
    def __init__(self, description_cas: str, initial_context: dict, workflow_id: str = None):
        super().__init__(initial_context, workflow_id)
        self.description_cas: str = description_cas
        self.elements_identifies: List[Dict] = [] # {element_id, type, description, source}
        self.belief_sets: Dict[str, str] = {} # {belief_set_id: serialized_content}
        self.query_log: List[Dict] = [] # Voir Section 5
        self.hypotheses_enquete: List[Dict] = [] # Voir Section 5

    # Méthodes pour la description du cas
    def get_case_description(self) -> str:
        # Placeholder implementation
        return self.description_cas

    def update_case_description(self, new_description: str) -> None:
        # Placeholder implementation
        self.description_cas = new_description

    # Méthodes pour les éléments identifiés
    def add_identified_element(self, element_type: str, description: str, source: str) -> dict:
        # Placeholder implementation
        new_element = {
            "element_id": str(uuid.uuid4()),
            "type": element_type,
            "description": description,
            "source": source
        }
        self.elements_identifies.append(new_element)
        return new_element

    def get_identified_elements(self, element_type: str = None) -> List[dict]:
        # Placeholder implementation
        if element_type:
            return [e for e in self.elements_identifies if e.get("type") == element_type]
        return self.elements_identifies

    # Méthodes pour les BeliefSets (gestion simplifiée du contenu)
    def add_or_update_belief_set(self, bs_id: str, content: str) -> None:
        # Placeholder implementation
        self.belief_sets[bs_id] = content

    def get_belief_set_content(self, bs_id: str) -> Optional[str]:
        # Placeholder implementation
        return self.belief_sets.get(bs_id)

    def remove_belief_set(self, bs_id: str) -> bool:
        # Placeholder implementation
        if bs_id in self.belief_sets:
            del self.belief_sets[bs_id]
            return True
        return False

    def list_belief_sets(self) -> List[str]:
        # Placeholder implementation
        return list(self.belief_sets.keys())

    # Méthodes pour le query_log
    def add_query_log_entry(self, queried_by: str, query_text_or_params: Any, belief_set_id_cible: str) -> str:
        # Placeholder implementation
        query_id = str(uuid.uuid4())
        self.query_log.append({
            "query_id": query_id,
            "queried_by": queried_by,
            "query_text_or_params": query_text_or_params,
            "belief_set_id_cible": belief_set_id_cible,
            "status_processing": "pending" # Example status
        })
        return query_id

    def update_query_log_status(self, query_id: str, status_processing: str) -> bool:
        # Placeholder implementation
        for entry in self.query_log:
            if entry["query_id"] == query_id:
                entry["status_processing"] = status_processing
                return True
        return False

    def get_query_log_entries(self, queried_by: str = None, belief_set_id_cible: str = None) -> List[dict]:
        # Placeholder implementation
        filtered_entries = self.query_log
        if queried_by:
            filtered_entries = [e for e in filtered_entries if e.get("queried_by") == queried_by]
        if belief_set_id_cible:
            filtered_entries = [e for e in filtered_entries if e.get("belief_set_id_cible") == belief_set_id_cible]
        return filtered_entries

    # Méthodes pour les hypothèses
    def add_hypothesis(self, text: str, confidence_score: float, hypothesis_id: str = None) -> dict:
        # Placeholder implementation
        new_hypothesis = {
            "hypothesis_id": hypothesis_id or str(uuid.uuid4()),
            "text": text,
            "confidence_score": confidence_score,
            "status": "new", # Example status
            "supporting_evidence_ids": [],
            "contradicting_evidence_ids": []
        }
        self.hypotheses_enquete.append(new_hypothesis)
        return new_hypothesis

    def get_hypothesis(self, hypothesis_id: str) -> Optional[dict]:
        # Placeholder implementation
        for h in self.hypotheses_enquete:
            if h["hypothesis_id"] == hypothesis_id:
                return h
        return None

    def update_hypothesis(self, hypothesis_id: str, new_text: str = None, new_confidence: float = None, new_status: str = None, \
                          add_supporting_evidence_id: str = None, add_contradicting_evidence_id: str = None) -> bool:
        # Placeholder implementation
        hypothesis = self.get_hypothesis(hypothesis_id)
        if not hypothesis:
            return False
        if new_text is not None:
            hypothesis["text"] = new_text
        if new_confidence is not None:
            hypothesis["confidence_score"] = new_confidence
        if new_status is not None:
            hypothesis["status"] = new_status
        if add_supporting_evidence_id:
            hypothesis["supporting_evidence_ids"].append(add_supporting_evidence_id)
        if add_contradicting_evidence_id:
            hypothesis["contradicting_evidence_ids"].append(add_contradicting_evidence_id)
        return True

    def get_hypotheses(self, status: str = None) -> List[dict]:
        # Placeholder implementation
        if status:
            return [h for h in self.hypotheses_enquete if h.get("status") == status]
        return self.hypotheses_enquete

class EnqueteCluedoState(EnquetePoliciereState):
    def __init__(self, nom_enquete_cluedo: str, elements_jeu_cluedo: dict, \
                 description_cas: str, initial_context: dict, workflow_id: str = None, \
                 solution_secrete_cluedo: dict = None, auto_generate_solution: bool = True):
        super().__init__(description_cas, initial_context, workflow_id)
        self.nom_enquete_cluedo: str = nom_enquete_cluedo
        self.elements_jeu_cluedo: dict = elements_jeu_cluedo # {"suspects": [], "armes": [], "lieux": []}
        
        if solution_secrete_cluedo:
            self.solution_secrete_cluedo: dict = solution_secrete_cluedo # {"suspect": "X", "arme": "Y", "lieu": "Z"}
        elif auto_generate_solution:
            self.solution_secrete_cluedo: dict = self._generate_random_solution()
        else:
            raise ValueError("Une solution secrète doit être fournie ou auto-générée.")

        self.indices_distribues_cluedo: List[Dict] = [] # Liste d'éléments qui ne sont PAS la solution
        self.main_cluedo_bs_id: str = f"cluedo_bs_{self.workflow_id}"
        self.belief_set_initial_watson: Dict[str, List[str]] = {} # Initialisation de l'attribut
        self.is_solution_proposed: bool = False
        self.final_solution: Optional[Dict[str, str]] = None
        self.suggestions_historique: List[Dict] = []
        
        self._initialize_cluedo_belief_set()

    def _generate_random_solution(self) -> dict:
        """
        Génère une solution aléatoire pour le Cluedo en sélectionnant un suspect,
        une arme et un lieu parmi les éléments de jeu fournis.
        """
        # Assurer que les listes ne sont pas vides pour éviter random.choice sur une séquence vide
        suspects = self.elements_jeu_cluedo.get("suspects")
        if not suspects:
            raise ValueError("La liste des suspects ne peut pas être vide pour générer une solution.")
        
        armes = self.elements_jeu_cluedo.get("armes")
        if not armes:
            raise ValueError("La liste des armes ne peut pas être vide pour générer une solution.")
            
        lieux = self.elements_jeu_cluedo.get("lieux")
        if not lieux:
            raise ValueError("La liste des lieux ne peut pas être vide pour générer une solution.")

        suspect = random.choice(suspects)
        arme = random.choice(armes)
        lieu = random.choice(lieux)
        return {"suspect": suspect, "arme": arme, "lieu": lieu}

    def _initialize_cluedo_belief_set(self):
        """
        Initialise le belief_set_initial_watson avec des informations sur les éléments
        qui ne font PAS partie de la solution secrète.
        Initialise également le belief_set formel pour Watson.
        """
        self.belief_set_initial_watson = {
            "suspects_exclus": [],
            "armes_exclues": [],
            "lieux_exclus": []
        }
        initial_formulas: List[str] = []

        # Traitement des suspects
        solution_suspect = self.solution_secrete_cluedo.get("suspect")
        for suspect in self.elements_jeu_cluedo.get("suspects", []):
            if suspect != solution_suspect:
                self.belief_set_initial_watson["suspects_exclus"].append(f"{suspect} n'est pas le meurtrier.")
                initial_formulas.append(f"Not(Coupable({suspect}))") # Structure de formule placeholder

        # Traitement des armes
        solution_arme = self.solution_secrete_cluedo.get("arme")
        for arme in self.elements_jeu_cluedo.get("armes", []):
            if arme != solution_arme:
                self.belief_set_initial_watson["armes_exclues"].append(f"{arme} n'est pas l'arme du crime.")
                initial_formulas.append(f"Not(Arme({arme}))") # Structure de formule placeholder
        
        # Traitement des lieux
        solution_lieu = self.solution_secrete_cluedo.get("lieu")
        for lieu in self.elements_jeu_cluedo.get("lieux", []):
            if lieu != solution_lieu:
                self.belief_set_initial_watson["lieux_exclus"].append(f"{lieu} n'est pas le lieu du crime.")
                initial_formulas.append(f"Not(Lieu({lieu}))") # Structure de formule placeholder

        # Mise à jour du belief set formel pour Watson (logique existante conservée)
        self.add_or_update_belief_set(self.main_cluedo_bs_id, "\n".join(initial_formulas))

    def get_solution_secrete(self) -> Optional[dict]:
        # ATTENTION: Cette méthode ne devrait être accessible qu'à l'orchestrateur/évaluateur,
        # pas directement aux agents via StateManagerPlugin.
        # Des mécanismes de contrôle d'accès pourraient être nécessaires.
        return self.solution_secrete_cluedo

    def get_elements_jeu(self) -> dict:
        return self.elements_jeu_cluedo

    def propose_final_solution(self, solution: Dict[str, str]):
        """
        Enregistre la solution finale proposée par un agent et met à jour l'état.
        La solution doit être un dictionnaire avec les clés 'suspect', 'arme', 'lieu'.
        """
        if not all(k in solution for k in ["suspect", "arme", "lieu"]):
            raise ValueError("La solution proposée est invalide. Elle doit contenir 'suspect', 'arme', et 'lieu'.")
        
        self.final_solution = solution
        self.is_solution_proposed = True
        # On pourrait aussi ajouter un log ici
        self.add_log_message(
            agent_source="System",
            message_type="solution_proposed",
            content=f"Solution finale proposée: {solution}"
        )

    # D'autres méthodes spécifiques au Cluedo pourraient être ajoutées ici,
    # par exemple pour gérer les "suggestions" des joueurs, etc.