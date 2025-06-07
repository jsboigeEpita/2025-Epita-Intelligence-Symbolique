# 🔧 Architecture Technique Détaillée - Système Sherlock-Watson-Moriarty
## Intégrations, Optimisations et Workarounds Techniques

> **Guide technique approfondi pour développeurs et architectes**  
> Semantic Kernel v1.29.0 + Tweety JVM + Workarounds Pydantic - Janvier 2025

---

## 📚 **NAVIGATION RAPIDE**

| 🎯 **Section** | 🛠️ **Technologie** | 🔗 **Liens Associés** |
|----------------|-------------------|----------------------|
| [⚙️ Semantic Kernel](#️-intégration-semantic-kernel) | v1.29.0 | [📖 Index Principal](README.md) |
| [☕ Bridge Tweety JVM](#-bridge-tweety-jvm) | JPype1 + 35 JARs | [🏗️ Architecture](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md) |
| [🔄 Workarounds Pydantic](#-workarounds-pydantic) | object.__setattr__() | [🛠️ Guide Utilisateur](GUIDE_UTILISATEUR_COMPLET.md) |
| [🎭 Orchestration Cyclique](#-orchestration-cyclique) | 3-agents workflow | [📊 Analyse Orchestrations](../analyse_orchestrations_sherlock_watson.md) |
| [⚡ Performance](#-performance-et-optimisation) | Monitoring + Cache | [📋 Rapport Oracle](RAPPORT_MISSION_ORACLE_ENHANCED.md) |

---

## ⚙️ **INTÉGRATION SEMANTIC KERNEL**

### 🏗️ **Architecture Semantic Kernel v1.29.0**

#### Vue d'Ensemble Technique
```mermaid
graph TB
    subgraph "🤖 SEMANTIC KERNEL CORE"
        SK1[Kernel Instance]
        SK2[ChatCompletionService]
        SK3[OpenAIChatCompletion]
        SK4[FunctionChoiceBehavior.Auto]
    end
    
    subgraph "🎭 AGENTS LAYER"
        A1[ChatCompletionAgent - Sherlock]
        A2[ChatCompletionAgent - Watson]
        A3[ChatCompletionAgent - Moriarty]
    end
    
    subgraph "🔧 PLUGINS LAYER"
        P1[StateManagerPlugin]
        P2[TweetyBridgePlugin]
        P3[OracleDatasetPlugin]
    end
    
    subgraph "🔄 ORCHESTRATION LAYER"
        O1[AgentGroupChat]
        O2[SelectionStrategy]
        O3[TerminationStrategy]
    end
    
    SK1 --> A1
    SK1 --> A2
    SK1 --> A3
    
    A1 --> P1
    A2 --> P2
    A3 --> P3
    
    O1 --> A1
    O1 --> A2
    O1 --> A3
```

#### Configuration Kernel Optimisée
```python
class OptimizedKernelBuilder:
    """
    Configuration Semantic Kernel optimisée pour workflows multi-agents
    """
    
    @staticmethod
    def build_kernel() -> Kernel:
        # Builder avec configuration optimale
        builder = Kernel.builder()
        
        # Service OpenAI configuré pour performance
        chat_service = OpenAIChatCompletion(
            api_key=settings.OPENAI_API_KEY,
            ai_model_id="gpt-4o-mini",
            service_id="openai_chat",
            # Optimisations performance
            max_tokens=2000,
            temperature=0.3,
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0
        )
        
        # Ajout service avec fallback
        builder.add_service(chat_service)
        
        # Configuration logging pour debug
        builder.add_service(
            ConsoleLogger(log_level=LogLevel.INFO)
        )
        
        return builder.build()
```

#### Agents ChatCompletion Avancés
```python
class SherlockEnqueteAgent(ChatCompletionAgent):
    """
    Agent Sherlock avec configuration Semantic Kernel optimisée
    """
    
    def __init__(self, kernel: Kernel, state_manager: StateManagerPlugin):
        # Instructions spécialisées avec context injection
        instructions = self._build_dynamic_instructions()
        
        super().__init__(
            service_id="openai_chat",
            kernel=kernel,
            name="SherlockEnqueteAgent",
            instructions=instructions,
            # Configuration fonction choice automatique
            execution_settings=self._get_execution_settings()
        )
        
        # Injection plugins avec validation
        self._inject_plugins(state_manager)
    
    def _get_execution_settings(self) -> OpenAIChatPromptExecutionSettings:
        """Configuration exécution optimisée pour Sherlock"""
        return OpenAIChatPromptExecutionSettings(
            service_id="openai_chat",
            max_tokens=1500,
            temperature=0.3,
            # Activation fonction choice automatique
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                auto_invoke=True,
                filters={"included_plugins": ["StateManagerPlugin"]}
            ),
            # Optimisations stream et cache
            stream=False,
            cache_enabled=True
        )
    
    def _inject_plugins(self, state_manager: StateManagerPlugin):
        """Injection sécurisée des plugins avec validation"""
        try:
            # Validation plugin avant injection
            if not isinstance(state_manager, StateManagerPlugin):
                raise TypeError("state_manager must be StateManagerPlugin instance")
            
            # Injection avec gestion d'erreurs
            self.kernel.add_plugin(state_manager, plugin_name="StateManagerPlugin")
            
            # Validation post-injection
            if "StateManagerPlugin" not in self.kernel.plugins:
                raise RuntimeError("Plugin injection failed")
                
        except Exception as e:
            logger.error(f"Plugin injection failed for {self.name}: {e}")
            raise
```

### 🔧 **Plugins Semantic Kernel Personnalisés**

#### StateManagerPlugin - Gestion d'État Centralisée
```python
class StateManagerPlugin:
    """
    Plugin Semantic Kernel pour gestion centralisée de l'état partagé
    Expose les méthodes d'état comme fonctions sémantiques
    """
    
    def __init__(self, shared_state: BaseWorkflowState):
        self.shared_state = shared_state
        self.access_log = []
        self.performance_tracker = PerformanceTracker()
    
    @kernel_function(
        description="Ajouter une nouvelle hypothèse à l'enquête",
        name="add_hypothesis"
    )
    def add_hypothesis(
        self, 
        hypothesis_text: Annotated[str, "Texte de l'hypothèse"],
        confidence_score: Annotated[float, "Score de confiance 0.0-1.0"]
    ) -> str:
        """
        Fonction sémantique pour ajout d'hypothèse
        Accessible via FunctionChoiceBehavior.Auto par les agents
        """
        with self.performance_tracker.track("add_hypothesis"):
            try:
                # Validation entrées
                if not hypothesis_text or confidence_score < 0 or confidence_score > 1:
                    raise ValueError("Invalid hypothesis parameters")
                
                # Ajout avec logging
                hypothesis = self.shared_state.add_hypothesis(
                    text=hypothesis_text,
                    confidence_score=confidence_score
                )
                
                # Tracking d'accès
                self._log_access("add_hypothesis", hypothesis["hypothesis_id"])
                
                return f"Hypothèse ajoutée avec ID: {hypothesis['hypothesis_id']}"
                
            except Exception as e:
                logger.error(f"add_hypothesis failed: {e}")
                return f"Erreur lors de l'ajout: {e}"
    
    @kernel_function(
        description="Faire une suggestion Cluedo (suspect, arme, lieu)",
        name="faire_suggestion"
    )
    def faire_suggestion(
        self,
        suspect: Annotated[str, "Nom du suspect suggéré"],
        arme: Annotated[str, "Arme suggérée"],
        lieu: Annotated[str, "Lieu suggéré"]
    ) -> str:
        """
        Fonction spécialisée Cluedo avec détection automatique
        """
        with self.performance_tracker.track("faire_suggestion"):
            suggestion = {
                "suspect": suspect.strip(),
                "arme": arme.strip(), 
                "lieu": lieu.strip()
            }
            
            # Validation éléments Cluedo
            if not self._validate_cluedo_elements(suggestion):
                return "Suggestion invalide: éléments non reconnus"
            
            # Enregistrement suggestion
            self.shared_state.add_suggestion(suggestion)
            
            # Trigger automatique Oracle (si présent)
            if hasattr(self.shared_state, 'trigger_oracle_response'):
                oracle_response = self.shared_state.trigger_oracle_response(suggestion)
                return f"Suggestion enregistrée. Oracle: {oracle_response}"
            
            return f"Suggestion enregistrée: {suspect} avec {arme} dans {lieu}"
```

#### TweetyBridgePlugin - Intégration Logique Formelle
```python
class TweetyBridgePlugin:
    """
    Plugin pour intégration TweetyProject via JPype1
    Gestion optimisée des requêtes logiques avec pool de connexions
    """
    
    def __init__(self, jar_path: str, pool_size: int = 3):
        self.jar_path = jar_path
        self.jvm_pool = JVMConnectionPool(pool_size)
        self.query_cache = LRUCache(maxsize=1000)
        self.performance_metrics = TweetyPerformanceMetrics()
    
    @kernel_function(
        description="Valider syntaxe d'une formule logique",
        name="validate_formula"
    )
    def validate_formula(
        self,
        formula_text: Annotated[str, "Formule logique à valider"]
    ) -> str:
        """
        Validation syntaxique BNF avec normalisation automatique
        """
        with self.performance_metrics.track("validate_formula"):
            try:
                # Normalisation pour parser Tweety
                normalized_formula = self._normalize_formula(formula_text)
                
                # Validation via pool JVM
                with self.jvm_pool.get_connection() as jvm_bridge:
                    is_valid = jvm_bridge.validate_syntax(normalized_formula)
                    
                if is_valid:
                    return f"✅ Formule valide: {normalized_formula}"
                else:
                    return f"❌ Formule invalide: erreurs syntaxiques détectées"
                    
            except Exception as e:
                logger.error(f"Formula validation failed: {e}")
                return f"Erreur validation: {e}"
    
    @kernel_function(
        description="Exécuter requête logique TweetyProject",
        name="execute_query"
    )
    def execute_query(
        self,
        query_formula: Annotated[str, "Formule de requête"],
        belief_set_id: Annotated[str, "ID du belief set à interroger"]
    ) -> str:
        """
        Exécution optimisée avec cache et retry automatique
        """
        # Clé cache pour optimisation
        cache_key = hashlib.md5(f"{query_formula}:{belief_set_id}".encode()).hexdigest()
        
        # Vérification cache
        if cached_result := self.query_cache.get(cache_key):
            self.performance_metrics.record_cache_hit()
            return cached_result
        
        with self.performance_metrics.track("execute_query"):
            try:
                # Normalisation requête
                normalized_query = self._normalize_formula(query_formula)
                
                # Exécution avec retry automatique
                result = self._execute_with_retry(
                    query=normalized_query,
                    belief_set_id=belief_set_id,
                    max_retries=3
                )
                
                # Cache du résultat
                self.query_cache[cache_key] = result
                
                return result
                
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                return f"Erreur exécution: {e}"
```

---

## ☕ **BRIDGE TWEETY JVM**

### 🚀 **Configuration JPype1 Optimisée**

#### Initialisation JVM avec Pool de Connexions
```python
class JVMConnectionPool:
    """
    Pool de connexions JVM optimisé pour requêtes parallèles TweetyProject
    Gestion automatique lifecycle + monitoring performance
    """
    
    def __init__(self, pool_size: int = 3, max_heap: str = "4G"):
        self.pool_size = pool_size
        self.max_heap = max_heap
        self.connections = Queue(maxsize=pool_size)
        self.active_connections = 0
        self.performance_stats = JVMPerformanceStats()
        
        # Initialisation pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialisation sécurisée du pool JVM"""
        try:
            # Configuration JVM avec optimisations
            jvm_args = [
                f"-Xmx{self.max_heap}",
                f"-Xms{int(self.max_heap[:-1])//2}G",  # Heap initial = 50% max
                "-XX:+UseG1GC",                          # Garbage collector optimisé
                "-XX:+UseStringDeduplication",           # Optimisation mémoire strings
                "-Djava.awt.headless=true"               # Mode headless
            ]
            
            # Démarrage JVM si pas déjà active
            if not jpype.isJVMStarted():
                jpype.startJVM(
                    jpype.getDefaultJVMPath(),
                    *jvm_args,
                    classpath=self._build_classpath()
                )
            
            # Création pool connexions
            for i in range(self.pool_size):
                connection = TweetyBridgeConnection(connection_id=i)
                self.connections.put(connection)
                
            logger.info(f"JVM Pool initialized: {self.pool_size} connections")
            
        except Exception as e:
            logger.error(f"JVM Pool initialization failed: {e}")
            raise
    
    def _build_classpath(self) -> List[str]:
        """Construction classpath avec tous les JAR Tweety"""
        jar_path = Path("libs")
        jar_files = list(jar_path.glob("*.jar"))
        
        if len(jar_files) < 35:
            logger.warning(f"Only {len(jar_files)} JAR files found, expected 35+")
        
        classpath = [str(jar) for jar in jar_files]
        logger.info(f"Classpath built: {len(classpath)} JAR files")
        
        return classpath
    
    @contextmanager
    def get_connection(self) -> TweetyBridgeConnection:
        """Context manager pour connexion avec auto-release"""
        connection = None
        try:
            # Acquisition connexion avec timeout
            connection = self.connections.get(timeout=30.0)
            self.active_connections += 1
            
            yield connection
            
        except Empty:
            raise TimeoutError("No JVM connection available within timeout")
        finally:
            # Release automatique connexion
            if connection:
                self.connections.put(connection)
                self.active_connections -= 1
```

#### Bridge Connection Optimisée
```python
class TweetyBridgeConnection:
    """
    Connexion individuelle TweetyProject avec gestion robuste des erreurs
    """
    
    def __init__(self, connection_id: int):
        self.connection_id = connection_id
        self.java_imports = self._import_tweety_classes()
        self.belief_sets_cache = {}
        self.query_counter = 0
    
    def _import_tweety_classes(self) -> Dict[str, Any]:
        """Import optimisé des classes Tweety avec gestion d'erreurs"""
        try:
            # Classes essentielles TweetyProject
            imports = {
                # Logique propositionnelle
                'PlSignature': jpype.JClass('org.tweetyproject.logics.pl.syntax.PlSignature'),
                'PlBeliefSet': jpype.JClass('org.tweetyproject.logics.pl.syntax.PlBeliefSet'),
                'PlParser': jpype.JClass('org.tweetyproject.logics.pl.parser.PlParser'),
                'PlFormula': jpype.JClass('org.tweetyproject.logics.pl.syntax.PlFormula'),
                
                # Raisonnement
                'SatSolver': jpype.JClass('org.tweetyproject.logics.pl.sat.SatSolver'),
                'Sat4jSolver': jpype.JClass('org.tweetyproject.logics.pl.sat.Sat4jSolver'),
                
                # Utilitaires
                'Proposition': jpype.JClass('org.tweetyproject.logics.pl.syntax.Proposition'),
                'Negation': jpype.JClass('org.tweetyproject.logics.pl.syntax.Negation'),
                'Conjunction': jpype.JClass('org.tweetyproject.logics.pl.syntax.Conjunction'),
                'Disjunction': jpype.JClass('org.tweetyproject.logics.pl.syntax.Disjunction')
            }
            
            # Validation imports
            for name, java_class in imports.items():
                if java_class is None:
                    raise ImportError(f"Failed to import {name}")
            
            logger.info(f"Tweety imports successful: {len(imports)} classes")
            return imports
            
        except Exception as e:
            logger.error(f"Tweety import failed: {e}")
            raise
    
    def perform_pl_query(self, formula: str, belief_set_id: str) -> Dict[str, Any]:
        """
        Exécution requête propositionnelle avec gestion complète d'erreurs
        """
        self.query_counter += 1
        start_time = time.time()
        
        try:
            # Récupération/création belief set
            belief_set = self._get_or_create_belief_set(belief_set_id)
            
            # Parsing formule avec validation
            parser = self.java_imports['PlParser']()
            parsed_formula = parser.parseFormula(formula)
            
            # Configuration solveur
            solver = self.java_imports['Sat4jSolver']()
            
            # Exécution requête
            result = solver.query(belief_set, parsed_formula)
            
            # Formatage résultat
            execution_time = time.time() - start_time
            
            return {
                'result': str(result),
                'satisfiable': result.toString() == "true",
                'execution_time': execution_time,
                'query_id': f"q_{self.connection_id}_{self.query_counter}",
                'belief_set_size': belief_set.size()
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                'result': 'ERROR',
                'error': str(e),
                'execution_time': time.time() - start_time,
                'query_id': f"q_{self.connection_id}_{self.query_counter}_ERROR"
            }
```

### 📊 **35+ JAR Files Management**

#### Vérification et Validation JAR Files
```python
class TweetyJarManager:
    """
    Gestionnaire pour validation et monitoring des JAR files Tweety
    """
    
    REQUIRED_JARS = {
        # Core Tweety
        'tweety-commons': 'org.tweetyproject.commons',
        'tweety-logics-pl': 'org.tweetyproject.logics.pl',
        'tweety-logics-commons': 'org.tweetyproject.logics.commons',
        
        # SAT Solvers
        'sat4j-core': 'org.sat4j.core',
        'sat4j-pb': 'org.sat4j.pb',
        
        # Math et utilitaires
        'tweety-math': 'org.tweetyproject.math',
        'commons-math3': 'org.apache.commons.math3',
        
        # Parsing
        'antlr4-runtime': 'org.antlr.v4.runtime',
        
        # Logging et IO
        'slf4j-api': 'org.slf4j',
        'logback-classic': 'ch.qos.logback.classic'
    }
    
    def __init__(self, jar_directory: Path):
        self.jar_directory = Path(jar_directory)
        self.available_jars = {}
        self.missing_jars = []
        
    def validate_jars(self) -> Dict[str, Any]:
        """Validation complète de tous les JAR files requis"""
        validation_report = {
            'total_jars_found': 0,
            'required_jars_found': 0,
            'missing_jars': [],
            'unknown_jars': [],
            'jar_details': {}
        }
        
        # Scan répertoire JAR
        jar_files = list(self.jar_directory.glob("*.jar"))
        validation_report['total_jars_found'] = len(jar_files)
        
        # Validation chaque JAR requis
        for jar_name, expected_package in self.REQUIRED_JARS.items():
            found_jar = self._find_jar_by_pattern(jar_files, jar_name)
            
            if found_jar:
                validation_report['jar_details'][jar_name] = {
                    'file': found_jar.name,
                    'size': found_jar.stat().st_size,
                    'package_validated': self._validate_jar_package(found_jar, expected_package)
                }
                validation_report['required_jars_found'] += 1
            else:
                validation_report['missing_jars'].append(jar_name)
        
        # JAR files non reconnus
        known_patterns = list(self.REQUIRED_JARS.keys())
        for jar_file in jar_files:
            if not any(pattern in jar_file.name for pattern in known_patterns):
                validation_report['unknown_jars'].append(jar_file.name)
        
        return validation_report
    
    def _validate_jar_package(self, jar_path: Path, expected_package: str) -> bool:
        """Validation que le JAR contient le package attendu"""
        try:
            import zipfile
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # Conversion package en chemin
                package_path = expected_package.replace('.', '/')
                
                # Recherche fichiers .class dans le package
                class_files = [f for f in jar.namelist() 
                             if f.startswith(package_path) and f.endswith('.class')]
                
                return len(class_files) > 0
                
        except Exception as e:
            logger.warning(f"Could not validate package in {jar_path}: {e}")
            return False
```

---

## 🔄 **WORKAROUNDS PYDANTIC**

### 🐍 **Problèmes Pydantic v2.10.3**

#### Diagnostic des Incompatibilités
```python
class PydanticCompatibilityManager:
    """
    Gestionnaire pour workarounds Pydantic v2 avec Semantic Kernel
    Résolution conflits validation + performance
    """
    
    def __init__(self):
        self.applied_workarounds = []
        self.compatibility_issues = []
        
    def apply_workarounds(self):
        """Application automatique de tous les workarounds nécessaires"""
        workarounds = [
            self._workaround_setattr_bypass,
            self._workaround_validation_mode,
            self._workaround_serialization_context,
            self._workaround_field_annotation
        ]
        
        for workaround in workarounds:
            try:
                workaround()
                self.applied_workarounds.append(workaround.__name__)
            except Exception as e:
                self.compatibility_issues.append({
                    'workaround': workaround.__name__,
                    'error': str(e)
                })
                logger.warning(f"Workaround {workaround.__name__} failed: {e}")
    
    def _workaround_setattr_bypass(self):
        """
        Workaround principal: Bypass validation Pydantic avec object.__setattr__()
        Nécessaire pour modification dynamique des attributs agents
        """
        def safe_setattr(obj, name: str, value: Any):
            """Setattr sécurisé qui bypass validation Pydantic si nécessaire"""
            try:
                # Tentative setattr normal
                setattr(obj, name, value)
            except (ValidationError, ValueError) as e:
                # Fallback avec object.__setattr__ pour bypass validation
                logger.debug(f"Using object.__setattr__ bypass for {obj.__class__.__name__}.{name}")
                object.__setattr__(obj, name, value)
        
        # Injection globale dans le namespace
        import builtins
        builtins.safe_setattr = safe_setattr
        
        logger.info("Pydantic setattr bypass workaround applied")
    
    def _workaround_validation_mode(self):
        """
        Configuration validation mode pour compatibilité Semantic Kernel
        """
        from pydantic import ConfigDict
        
        # Configuration globale plus permissive
        default_config = ConfigDict(
            validate_assignment=False,      # Disable validation sur assignment
            arbitrary_types_allowed=True,   # Autoriser types arbitraires
            extra='allow',                  # Autoriser attributs extra
            frozen=False,                   # Disable immutabilité
            use_enum_values=True,          # Utiliser valeurs enum
            validate_default=False,         # Disable validation des defaults
            str_strip_whitespace=True      # Strip whitespace sur strings
        )
        
        # Application aux classes concernées
        self._apply_config_to_classes(default_config)
        
        logger.info("Pydantic validation mode workaround applied")
    
    def _apply_config_to_classes(self, config: ConfigDict):
        """Application configuration aux classes problématiques"""
        target_classes = [
            'BaseWorkflowState',
            'EnqueteCluedoState', 
            'CluedoOracleState',
            'StateManagerPlugin'
        ]
        
        for class_name in target_classes:
            try:
                # Recherche classe dans modules importés
                cls = self._find_class_by_name(class_name)
                if cls and hasattr(cls, 'model_config'):
                    # Application configuration via object.__setattr__
                    object.__setattr__(cls, 'model_config', config)
                    logger.debug(f"Applied config to {class_name}")
            except Exception as e:
                logger.warning(f"Could not apply config to {class_name}: {e}")
```

#### Workarounds Spécifiques par Composant
```python
class SherlockStateWorkarounds:
    """
    Workarounds spécialisés pour les états Sherlock/Watson
    """
    
    @staticmethod
    def fix_state_dynamic_attributes():
        """
        Fix pour ajout dynamique d'attributs aux états
        Nécessaire pour extensions Oracle
        """
        def patched_setattr(self, name: str, value: Any):
            """Setattr patché pour états avec gestion Pydantic"""
            try:
                # Validation si attribut existe déjà
                if hasattr(self, name):
                    object.__setattr__(self, name, value)
                else:
                    # Nouvel attribut - ajout à __dict__ direct
                    self.__dict__[name] = value
                    
            except Exception as e:
                logger.error(f"Dynamic attribute setting failed: {e}")
                # Fallback ultime
                object.__setattr__(self, name, value)
        
        # Injection dans classes d'état
        from argumentation_analysis.core.enquete_states import BaseWorkflowState
        BaseWorkflowState.__setattr__ = patched_setattr
    
    @staticmethod  
    def fix_plugin_serialization():
        """
        Fix pour sérialisation plugins Semantic Kernel
        """
        def custom_serializer(obj):
            """Sérialiseur personnalisé pour objets complexes"""
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '__dict__'):
                return {k: v for k, v in obj.__dict__.items() 
                       if not k.startswith('_')}
            else:
                return str(obj)
        
        # Application aux classes plugin
        import json
        json.default_serializer = custom_serializer
```

---

## 🎭 **ORCHESTRATION CYCLIQUE**

### 🔄 **Stratégies de Sélection Avancées**

#### CyclicSelectionStrategy Enhanced
```python
class EnhancedCyclicSelectionStrategy:
    """
    Stratégie cyclique avancée avec adaptations contextuelles
    Support workflow 2-agents et 3-agents avec Oracle
    """
    
    def __init__(self, turn_order: List[str], adaptation_enabled: bool = True):
        self.turn_order = turn_order
        self.current_index = 0
        self.adaptation_enabled = adaptation_enabled
        self.context_analyzer = ContextAnalyzer()
        self.performance_tracker = SelectionPerformanceTracker()
    
    def select_next_speaker(self, agents: List[Agent], history: ChatHistory) -> Agent:
        """
        Sélection next speaker avec adaptations contextuelles intelligentes
        """
        with self.performance_tracker.track("select_next_speaker"):
            # Sélection de base (cyclique)
            base_selection = self.turn_order[self.current_index]
            
            # Adaptations contextuelles si activées
            if self.adaptation_enabled:
                adapted_selection = self._apply_contextual_adaptations(
                    base_selection, history
                )
            else:
                adapted_selection = base_selection
            
            # Mise à jour index cyclique
            self.current_index = (self.current_index + 1) % len(self.turn_order)
            
            # Résolution agent par nom
            selected_agent = self._resolve_agent_by_name(agents, adapted_selection)
            
            # Logging de la sélection
            self._log_selection(adapted_selection, base_selection != adapted_selection)
            
            return selected_agent
    
    def _apply_contextual_adaptations(self, base_selection: str, history: ChatHistory) -> str:
        """
        Application d'adaptations contextuelles intelligentes
        """
        context = self.context_analyzer.analyze_recent_context(history)
        
        # Adaptation 1: Priorité Oracle après suggestion Sherlock
        if (context.last_action == "suggestion_cluedo" and 
            context.last_agent == "sherlock" and
            "moriarty" in self.turn_order):
            return "moriarty"  # Force Oracle response
        
        # Adaptation 2: Retour Sherlock après révélation Oracle critique
        if (context.last_action == "oracle_revelation" and
            context.revelation_impact > 0.8):
            return "sherlock"  # Force Sherlock integration
        
        # Adaptation 3: Watson focus si logique complexe détectée
        if (context.complexity_score > 0.7 and
            context.watson_idle_turns > 2):
            return "watson"  # Force Watson engagement
        
        # Pas d'adaptation nécessaire
        return base_selection
    
    def _log_selection(self, selected: str, adapted: bool):
        """Logging détaillé des sélections pour analyse"""
        log_entry = {
            'timestamp': datetime.now(),
            'selected_agent': selected,
            'was_adapted': adapted,
            'cycle_position': self.current_index,
            'strategy': 'enhanced_cyclic'
        }
        
        logger.info(f"Agent selected: {selected} {'(adapted)' if adapted else '(cyclic)'}")
        self.performance_tracker.log_selection(log_entry)
```

#### Termination Strategies Multi-Critères
```python
class OracleTerminationStrategy:
    """
    Stratégie de terminaison avancée pour workflows avec Oracle
    Multi-critères avec validation croisée
    """
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.criteria_evaluators = [
            SolutionProposedEvaluator(),
            OracleValidationEvaluator(), 
            ConsensusEvaluator(),
            ProgressStagnationEvaluator()
        ]
    
    def should_terminate(self, state: BaseWorkflowState, history: ChatHistory) -> bool:
        """
        Évaluation multi-critères pour terminaison intelligente
        """
        current_turn = len(history.messages)
        
        # Critère 1: Timeout absolu
        if current_turn >= self.max_turns:
            logger.info(f"Termination: Max turns reached ({self.max_turns})")
            return True
        
        # Évaluation critères spécialisés
        termination_scores = {}
        for evaluator in self.criteria_evaluators:
            score = evaluator.evaluate(state, history)
            termination_scores[evaluator.name] = score
        
        # Logique de décision composite
        decision = self._make_termination_decision(termination_scores)
        
        if decision:
            logger.info(f"Termination: {decision['reason']} (scores: {termination_scores})")
        
        return decision['should_terminate'] if decision else False
    
    def _make_termination_decision(self, scores: Dict[str, float]) -> Optional[Dict]:
        """
        Logique de décision composite pour terminaison
        """
        # Règle 1: Solution proposée ET validée Oracle
        if (scores.get('solution_proposed', 0) > 0.9 and 
            scores.get('oracle_validation', 0) > 0.8):
            return {
                'should_terminate': True,
                'reason': 'Solution validated by Oracle',
                'confidence': min(scores['solution_proposed'], scores['oracle_validation'])
            }
        
        # Règle 2: Consensus élevé entre agents
        if scores.get('consensus', 0) > 0.85:
            return {
                'should_terminate': True,
                'reason': 'High consensus achieved',
                'confidence': scores['consensus']
            }
        
        # Règle 3: Stagnation détectée
        if scores.get('progress_stagnation', 0) > 0.9:
            return {
                'should_terminate': True,
                'reason': 'Progress stagnation detected',
                'confidence': scores['progress_stagnation']
            }
        
        # Pas de terminaison
        return None

class SolutionProposedEvaluator:
    """Évaluateur pour détection de solutions proposées"""
    
    name = "solution_proposed"
    
    def evaluate(self, state: BaseWorkflowState, history: ChatHistory) -> float:
        """Détecte si une solution finale a été proposée"""
        if hasattr(state, 'is_solution_proposed') and state.is_solution_proposed:
            return 1.0
        
        # Recherche dans historique
        recent_messages = history.messages[-5:]  # 5 derniers messages
        solution_keywords = ['solution finale', 'ma solution', 'conclusion']
        
        for message in recent_messages:
            content = message.content.lower()
            if any(keyword in content for keyword in solution_keywords):
                return 0.8
        
        return 0.0

class OracleValidationEvaluator:
    """Évaluateur pour validation Oracle"""
    
    name = "oracle_validation"
    
    def evaluate(self, state: BaseWorkflowState, history: ChatHistory) -> float:
        """Évalue si l'Oracle a validé la solution"""
        if not hasattr(state, 'revelations_log'):
            return 0.0
        
        # Analyse des révélations Oracle récentes
        recent_revelations = state.revelations_log[-3:]  # 3 dernières
        validation_score = 0.0
        
        for revelation in recent_revelations:
            if 'cannot_refute' in revelation.get('response', '').lower():
                validation_score += 0.4
            elif 'no_contradiction' in revelation.get('response', '').lower():
                validation_score += 0.3
        
        return min(validation_score, 1.0)
```

---

## ⚡ **PERFORMANCE ET OPTIMISATION**

### 📊 **Monitoring en Temps Réel**

#### System Performance Tracker
```python
class SystemPerformanceTracker:
    """
    Monitoring performance système en temps réel
    Tracking agents, JVM, OpenAI, orchestration
    """
    
    def __init__(self):
        self.metrics = {
            'agents': AgentPerformanceMetrics(),
            'jvm': JVMPerformanceMetrics(),
            'openai': OpenAIPerformanceMetrics(),
            'orchestration': OrchestrationMetrics()
        }
        self.alert_thresholds = self._load_alert_thresholds()
        self.monitoring_active = True
    
    def start_monitoring(self):
        """Démarrage monitoring background"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # Thread monitoring agents
        threading.Thread(
            target=self._monitor_agents,
            daemon=True
        ).start()
        
        # Thread monitoring JVM
        threading.Thread(
            target=self._monitor_jvm_performance,
            daemon=True
        ).start()
        
        # Thread monitoring orchestration
        threading.Thread(
            target=self._monitor_orchestration,
            daemon=True
        ).start()
    
    def _monitor_agents(self):
        """Monitoring performance des agents"""
        while self.monitoring_active:
            try:
                # Métriques agents individuels
                for agent_name in ['sherlock', 'watson', 'moriarty']:
                    metrics = self.metrics['agents'].get_current_metrics(agent_name)
                    
                    # Alertes seuils
                    if metrics['response_time'] > self.alert_thresholds['agent_response_time']:
                        self._trigger_alert(f"Agent {agent_name} slow response: {metrics['response_time']:.2f}s")
                    
                    if metrics['error_rate'] > self.alert_thresholds['agent_error_rate']:
                        self._trigger_alert(f"Agent {agent_name} high error rate: {metrics['error_rate']:.2%}")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Agent monitoring error: {e}")
    
    def _monitor_jvm_performance(self):
        """Monitoring performance JVM Tweety"""
        while self.monitoring_active:
            try:
                jvm_metrics = self.metrics['jvm'].get_current_metrics()
                
                # Alertes mémoire
                if jvm_metrics['heap_usage'] > self.alert_thresholds['jvm_heap_usage']:
                    self._trigger_alert(f"JVM high heap usage: {jvm_metrics['heap_usage']:.1%}")
                
                # Alertes performance queries
                if jvm_metrics['avg_query_time'] > self.alert_thresholds['jvm_query_time']:
                    self._trigger_alert(f"JVM slow queries: {jvm_metrics['avg_query_time']:.2f}s")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"JVM monitoring error: {e}")

class AgentPerformanceMetrics:
    """Métriques performance spécifiques aux agents"""
    
    def __init__(self):
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        self.action_counts = defaultdict(lambda: defaultdict(int))
    
    def record_agent_interaction(self, agent_name: str, action: str, 
                               duration: float, success: bool):
        """Enregistrement interaction agent avec métriques"""
        self.response_times[agent_name].append(duration)
        self.action_counts[agent_name][action] += 1
        
        if success:
            self.success_counts[agent_name] += 1
        else:
            self.error_counts[agent_name] += 1
    
    def get_current_metrics(self, agent_name: str) -> Dict[str, float]:
        """Calcul métriques courantes pour un agent"""
        recent_times = self.response_times[agent_name][-10:]  # 10 dernières
        
        total_interactions = self.success_counts[agent_name] + self.error_counts[agent_name]
        
        return {
            'response_time': statistics.mean(recent_times) if recent_times else 0.0,
            'error_rate': self.error_counts[agent_name] / max(total_interactions, 1),
            'success_rate': self.success_counts[agent_name] / max(total_interactions, 1),
            'total_interactions': total_interactions,
            'actions_breakdown': dict(self.action_counts[agent_name])
        }
```

### 🚀 **Optimisations Cache**

#### Multi-Level Caching System
```python
class MultiLevelCacheSystem:
    """
    Système de cache multi-niveaux pour optimisation performance
    L1: Memory cache (LRU) - L2: Disk cache - L3: Network cache
    """
    
    def __init__(self):
        # L1 Cache: Mémoire (le plus rapide)
        self.memory_cache = LRUCache(maxsize=1000)
        
        # L2 Cache: Disque (persistant)
        self.disk_cache = DiskCache(
            directory='cache/sherlock_watson',
            size_limit=500 * 1024 * 1024  # 500MB
        )
        
        # L3 Cache: Réseau/Partagé (pour déploiements multi-instance)
        self.network_cache = None  # Configuré si disponible
        
        self.cache_stats = CacheStatistics()
    
    def get(self, key: str, cache_type: str = 'auto') -> Optional[Any]:
        """
        Récupération avec cascade cache L1 → L2 → L3
        """
        cache_key = self._normalize_key(key)
        
        # L1: Memory cache
        if value := self.memory_cache.get(cache_key):
            self.cache_stats.record_hit('L1')
            return value
        
        # L2: Disk cache
        if value := self.disk_cache.get(cache_key):
            self.cache_stats.record_hit('L2')
            # Promotion en L1
            self.memory_cache[cache_key] = value
            return value
        
        # L3: Network cache (si disponible)
        if self.network_cache and (value := self.network_cache.get(cache_key)):
            self.cache_stats.record_hit('L3')
            # Promotion en L2 et L1
            self.disk_cache.set(cache_key, value)
            self.memory_cache[cache_key] = value
            return value
        
        # Cache miss complet
        self.cache_stats.record_miss()
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Stockage avec réplication sur tous les niveaux
        """
        cache_key = self._normalize_key(key)
        
        # Stockage L1 (toujours)
        self.memory_cache[cache_key] = value
        
        # Stockage L2 (pour persistance)
        self.disk_cache.set(cache_key, value, ttl=ttl)
        
        # Stockage L3 (si disponible et valeur importante)
        if self.network_cache and self._is_valuable_for_sharing(value):
            self.network_cache.set(cache_key, value, ttl=ttl)
    
    def _is_valuable_for_sharing(self, value: Any) -> bool:
        """Détermine si une valeur mérite d'être partagée via network cache"""
        if isinstance(value, dict):
            # Résultats TweetyProject coûteux à recalculer
            if 'tweety_result' in value or 'belief_set' in value:
                return True
            # Solutions complètes Cluedo
            if 'solution' in value and 'validated' in value:
                return True
        
        return False

class TweetyQueryCache(MultiLevelCacheSystem):
    """Cache spécialisé pour requêtes TweetyProject"""
    
    def __init__(self):
        super().__init__()
        self.query_normalizer = TweetyQueryNormalizer()
    
    def get_cached_query_result(self, formula: str, belief_set_id: str) -> Optional[Dict]:
        """Récupération résultat requête avec normalisation"""
        # Normalisation pour améliorer hit rate
        normalized_formula = self.query_normalizer.normalize(formula)
        cache_key = f"tweety_query:{belief_set_id}:{normalized_formula}"
        
        return self.get(cache_key)
    
    def cache_query_result(self, formula: str, belief_set_id: str, 
                          result: Dict, ttl: int = 7200):
        """Cache résultat requête avec métadonnées"""
        normalized_formula = self.query_normalizer.normalize(formula)
        cache_key = f"tweety_query:{belief_set_id}:{normalized_formula}"
        
        # Enrichissement résultat avec métadonnées cache
        enriched_result = {
            **result,
            'cached_at': datetime.now().isoformat(),
            'original_formula': formula,
            'normalized_formula': normalized_formula
        }
        
        self.set(cache_key, enriched_result, ttl=ttl)
```

---

## 🔗 **LIENS DOCUMENTAIRES COMPLÉMENTAIRES**

### 📚 **Documentation Système**
- 🏗️ **[Architecture Complète](DOCUMENTATION_COMPLETE_SHERLOCK_WATSON.md)** - Vue d'ensemble système multi-agents
- 🛠️ **[Guide Utilisateur](GUIDE_UTILISATEUR_COMPLET.md)** - Installation, configuration, utilisation pratique
- 📖 **[Index Principal](README.md)** - Navigation centrale et accès rapide

### 📊 **Analyses et Rapports**
- 📈 **[Analyse Orchestrations](../analyse_orchestrations_sherlock_watson.md)** - Métriques performance, patterns efficacité
- 🎯 **[Rapport Oracle Enhanced](RAPPORT_MISSION_ORACLE_ENHANCED.md)** - Implémentation Oracle, corrections Moriarty

### 🔧 **Documentation Technique Externe**
- ⚙️ **[Semantic Kernel](https://learn.microsoft.com/semantic-kernel/)** - Documentation officielle Microsoft
- ☕ **[TweetyProject](http://tweetyproject.org/)** - Site officiel et documentation JAR
- 🐍 **[Pydantic v2](https://docs.pydantic.dev/latest/)** - Guide migration et workarounds
- 🤖 **[OpenAI API](https://platform.openai.com/docs)** - Documentation API et bonnes pratiques

---

## 🎯 **CONCLUSION TECHNIQUE**

Le système **Sherlock-Watson-Moriarty** représente une intégration technique avancée de **technologies disparates** pour créer un environnement de **raisonnement collaboratif robuste** :

### ✅ **Réussites Techniques Majeures**

1. **🔗 Intégration Multi-Technologies** 
   - Semantic Kernel v1.29.0 + OpenAI API
   - TweetyProject JVM + JPype1 bridge  
   - Pydantic v2 avec workarounds optimisés

2. **⚡ Optimisations Performance**
   - Pool connexions JVM pour parallélisme
   - Cache multi-niveaux (Memory + Disk + Network)
   - Monitoring temps réel avec alertes automatiques

3. **🛠️ Robustesse Technique**
   - Gestion d'erreurs multi-niveaux avec recovery
   - Workarounds Pydantic transparents et maintenables
   - Validation et fallbacks pour tous les composants critiques

### 🚀 **Innovations Architecturales**

1. **🎭 Orchestration Hybride** - Cyclique avec adaptations contextuelles intelligentes
2. **🔮 Oracle Pattern** - Révélations automatiques garantissant progression  
3. **🧩 Plugin Architecture** - Extensions modulaires via Semantic Kernel
4. **📊 Performance Monitoring** - Métriques temps réel pour optimisation continue

### 🔄 **Évolution Technique Continue**

Le système est conçu pour **évolution progressive** avec :
- **Extensibilité modulaire** pour nouveaux agents et domaines
- **Compatibilité versions** avec stratégies de migration automatisées
- **Scalabilité horizontale** via architecture distribuée
- **Innovation ML** pour orchestration adaptative future

---

**🔧 Document maintenu par :** Équipe Technique Sherlock/Watson  
**🔄 Dernière mise à jour :** Janvier 2025 - Oracle Enhanced + Optimisations  
**⏭️ Prochaine révision :** Mars 2025 - Extensions ML et Performance

**⚡ Le système Sherlock-Watson-Moriarty : Excellence technique au service du raisonnement collaboratif !**