/**
 * JTMS Dashboard JavaScript
 * ========================
 * 
 * Interface interactive pour la visualisation et manipulation du système JTMS.
 * Gère la visualisation Vis.js, les WebSockets temps réel, et les interactions utilisateur.
 * 
 * Version: 1.0.0
 * Auteur: Intelligence Symbolique EPITA
 * Date: 11/06/2025
 */

class JTMSDashboard {
    constructor() {
        this.network = null;
        this.nodes = new vis.DataSet([]);
        this.edges = new vis.DataSet([]);
        this.socket = null;
        this.currentSession = 'global';
        this.physicsEnabled = true;
        this.selectedNode = null;
        
        // Configuration couleurs
        this.colors = {
            valid: { background: '#28a745', border: '#1e7e34' },
            invalid: { background: '#dc3545', border: '#bd2130' },
            unknown: { background: '#ffc107', border: '#e0a800' },
            nonmonotonic: { background: '#fd7e14', border: '#fd7e14' }
        };
        
        this.initializeNetwork();
        this.setupSocketConnection();
        this.bindEventListeners();
        
        console.log('📊 JTMS Dashboard initialisé');
        this.logActivity('🚀 Dashboard JTMS prêt');
    }
    
    /**
     * Initialise le réseau de visualisation Vis.js
     */
    initializeNetwork() {
        const container = document.getElementById('network-container');
        if (!container) {
            console.error('❌ Container de visualisation introuvable');
            return;
        }
        
        // Configuration du réseau
        const data = {
            nodes: this.nodes,
            edges: this.edges
        };
        
        const options = {
            nodes: {
                shape: 'box',
                margin: 12,
                font: { 
                    size: 14,
                    face: 'Arial',
                    color: '#fff'
                },
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.2)',
                    size: 8,
                    x: 2,
                    y: 2
                },
                chosen: {
                    node: function(values, id, selected, hovering) {
                        values.shadow = true;
                        values.shadowSize = 12;
                        values.shadowColor = 'rgba(0,123,255,0.5)';
                    }
                }
            },
            edges: {
                arrows: { 
                    to: { 
                        enabled: true, 
                        scaleFactor: 1.2,
                        type: 'arrow'
                    } 
                },
                color: { 
                    inherit: false,
                    opacity: 0.8
                },
                width: 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.1)',
                    size: 4
                },
                smooth: {
                    enabled: true,
                    type: 'continuous',
                    roundness: 0.3
                }
            },
            physics: {
                enabled: true,
                stabilization: { 
                    iterations: 200,
                    updateInterval: 50
                },
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 120,
                    springConstant: 0.04,
                    damping: 0.2,
                    avoidOverlap: 0.1
                }
            },
            interaction: {
                hover: true,
                selectConnectedEdges: false,
                tooltipDelay: 300,
                hideEdgesOnDrag: false,
                hideNodesOnDrag: false
            },
            layout: {
                improvedLayout: true,
                clusterThreshold: 150
            }
        };
        
        try {
            this.network = new vis.Network(container, data, options);
            this.setupNetworkEvents();
            
            // Message initial dans le container
            if (this.nodes.length === 0) {
                this.showEmptyState();
            }
            
            console.log('✅ Réseau Vis.js initialisé');
        } catch (error) {
            console.error('❌ Erreur initialisation réseau:', error);
            this.logActivity('❌ Erreur initialisation visualisation');
        }
    }
    
    /**
     * Configure les événements du réseau
     */
    setupNetworkEvents() {
        if (!this.network) return;
        
        // Sélection de nœud
        this.network.on('selectNode', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                this.selectedNode = nodeId;
                this.showBeliefDetails(nodeId);
                this.highlightBeliefPath(nodeId);
            }
        });
        
        // Désélection
        this.network.on('deselectNode', () => {
            this.selectedNode = null;
            this.clearBeliefDetails();
            this.clearHighlight();
        });
        
        // Hover sur nœud
        this.network.on('hoverNode', (params) => {
            const nodeId = params.node;
            this.showNodeTooltip(nodeId, params.pointer.DOM);
        });
        
        // Double-clic pour édition
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                this.editBelief(nodeId);
            } else {
                // Double-clic sur zone vide = nouvelle croyance
                this.createBeliefAtPosition(params.pointer.canvas);
            }
        });
        
        // Stabilisation terminée
        this.network.on('stabilizationIterationsDone', () => {
            console.log('🎯 Stabilisation réseau terminée');
        });
    }
    
    /**
     * Configure la connexion WebSocket pour temps réel
     */
    setupSocketConnection() {
        try {
            // Tentative de connexion WebSocket (optionnelle)
            if (typeof io !== 'undefined') {
                this.socket = io();
                
                this.socket.on('connect', () => {
                    console.log('🔌 WebSocket connecté');
                    this.logActivity('🔌 Connexion temps réel activée');
                });
                
                this.socket.on('disconnect', () => {
                    console.log('🔌 WebSocket déconnecté');
                    this.logActivity('⚠️ Connexion temps réel perdue');
                });
                
                // Événements JTMS temps réel
                this.socket.on('belief_added', (data) => {
                    this.addBeliefToGraph(data.belief_name, data.belief_data);
                    this.logActivity(`✅ Croyance ajoutée: ${data.belief_name}`);
                    this.updateStatistics();
                });
                
                this.socket.on('justification_added', (data) => {
                    this.addJustificationToGraph(data);
                    this.logActivity(`🔗 Justification: ${data.in_list.join(', ')} ⊢ ${data.conclusion}`);
                    this.updateStatistics();
                });
                
                this.socket.on('belief_updated', (data) => {
                    this.updateBeliefInGraph(data.belief_name, data.belief_data);
                    this.logActivity(`📝 Croyance mise à jour: ${data.belief_name}`);
                });
                
                this.socket.on('consistency_check', (data) => {
                    this.handleConsistencyResult(data);
                });
                
            } else {
                console.warn('⚠️ Socket.IO non disponible - mode sans temps réel');
            }
        } catch (error) {
            console.warn('⚠️ WebSocket non configuré:', error);
        }
    }
    
    /**
     * Lie les événements de l'interface utilisateur
     */
    bindEventListeners() {
        // Gestion du redimensionnement
        window.addEventListener('resize', () => {
            if (this.network) {
                this.network.fit();
            }
        });
        
        // Raccourcis clavier
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 's':
                        e.preventDefault();
                        this.saveVisualization();
                        break;
                    case 'f':
                        e.preventDefault();
                        this.fitNetwork();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.resetView();
                        break;
                }
            }
            
            // Supprimer nœud sélectionné
            if (e.key === 'Delete' && this.selectedNode) {
                this.removeBelief(this.selectedNode);
            }
        });
    }
    
    /**
     * Charge les données d'une session JTMS
     */
    async loadSession(sessionId) {
        try {
            this.currentSession = sessionId;
            console.log(`📂 Chargement session: ${sessionId}`);
            
            const response = await fetch(`/jtms/api/session/${sessionId}`);
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const data = await response.json();
            this.loadJTMSData(data);
            this.updateStatistics(data.statistics);
            
            this.logActivity(`📂 Session "${sessionId}" chargée`);
            
        } catch (error) {
            console.error('❌ Erreur chargement session:', error);
            this.logActivity(`❌ Erreur chargement session: ${error.message}`);
            this.showNotification('Erreur lors du chargement de la session', 'error');
        }
    }
    
    /**
     * Charge les données JTMS dans la visualisation
     */
    loadJTMSData(data) {
        // Effacer les données existantes
        this.nodes.clear();
        this.edges.clear();
        
        console.log(`📊 Chargement ${Object.keys(data.beliefs || {}).length} croyances`);
        
        // Ajouter les croyances comme nœuds
        for (const [beliefName, beliefData] of Object.entries(data.beliefs || {})) {
            this.addBeliefToGraph(beliefName, beliefData, false);
        }
        
        // Ajouter les justifications comme arêtes
        for (const justification of data.justifications || []) {
            this.addJustificationToGraph(justification, false);
        }
        
        // Ajuster la vue
        setTimeout(() => {
            if (this.network && this.nodes.length > 0) {
                this.network.fit({
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }
                });
            } else {
                this.showEmptyState();
            }
        }, 500);
    }
    
    /**
     * Ajoute une croyance au graphe
     */
    addBeliefToGraph(beliefName, beliefData, animate = true) {
        const color = this.getBeliefColor(beliefData);
        const node = {
            id: beliefName,
            label: beliefName,
            color: color,
            title: this.getBeliefTooltip(beliefData),
            font: { 
                color: this.getTextColor(color.background)
            },
            chosen: true
        };
        
        this.nodes.update(node);
        
        if (animate && this.network) {
            // Animation d'apparition
            this.network.selectNodes([beliefName]);
            setTimeout(() => {
                this.network.unselectAll();
            }, 1000);
        }
    }
    
    /**
     * Détermine la couleur d'une croyance selon son état
     */
    getBeliefColor(beliefData) {
        if (beliefData.non_monotonic) {
            return this.colors.nonmonotonic;
        } else if (beliefData.valid === true) {
            return this.colors.valid;
        } else if (beliefData.valid === false) {
            return this.colors.invalid;
        } else {
            return this.colors.unknown;
        }
    }
    
    /**
     * Détermine la couleur du texte selon l'arrière-plan
     */
    getTextColor(backgroundColor) {
        // Couleurs sombres -> texte blanc, couleurs claires -> texte noir
        const darkColors = ['#28a745', '#dc3545', '#fd7e14'];
        return darkColors.includes(backgroundColor) ? '#ffffff' : '#000000';
    }
    
    /**
     * Génère le tooltip d'une croyance
     */
    getBeliefTooltip(beliefData) {
        const status = beliefData.non_monotonic ? 'Non-monotonic' :
                      beliefData.valid === true ? 'Valide' :
                      beliefData.valid === false ? 'Invalide' : 'Inconnu';
        
        let tooltip = `Statut: ${status}`;
        if (beliefData.justifications && beliefData.justifications.length > 0) {
            tooltip += `\nJustifications: ${beliefData.justifications.length}`;
        }
        if (beliefData.implications && beliefData.implications.length > 0) {
            tooltip += `\nImplications: ${beliefData.implications.length}`;
        }
        
        return tooltip;
    }
    
    /**
     * Ajoute une justification au graphe
     */
    addJustificationToGraph(justificationData, animate = true) {
        const { in_list, out_list, conclusion } = justificationData;
        
        // Arêtes depuis les prémisses positives
        for (const premise of in_list || []) {
            const edgeId = `${premise}->${conclusion}`;
            this.edges.update({
                id: edgeId,
                from: premise,
                to: conclusion,
                color: { color: '#28a745' },
                title: 'Prémisse positive',
                dashes: false,
                width: 2
            });
        }
        
        // Arêtes depuis les prémisses négatives  
        for (const negation of out_list || []) {
            const edgeId = `¬${negation}->${conclusion}`;
            this.edges.update({
                id: edgeId,
                from: negation,
                to: conclusion,
                color: { color: '#dc3545' },
                title: 'Prémisse négative',
                dashes: true,
                width: 2
            });
        }
    }
    
    /**
     * Affiche les détails d'une croyance sélectionnée
     */
    async showBeliefDetails(beliefName) {
        try {
            const response = await fetch(`/jtms/api/belief/${beliefName}?session=${this.currentSession}`);
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const data = await response.json();
            
            const detailsHtml = `
                <div class="belief-details-content">
                    <h6 class="fw-bold">${beliefName}</h6>
                    <p class="mb-2">
                        <strong>Statut:</strong> 
                        <span class="${this.getStatusClass(data)}">${this.getStatusText(data)}</span>
                    </p>
                    
                    ${data.justifications && data.justifications.length > 0 ? `
                        <h6 class="mt-3">Justifications:</h6>
                        <div class="justifications-list">
                            ${data.justifications.map((j, idx) => `
                                <div class="justification-item mb-2 p-2 border rounded bg-light">
                                    <small>
                                        <strong>IN:</strong> ${j.in_list.join(', ') || '-'}<br>
                                        <strong>OUT:</strong> ${j.out_list.join(', ') || '-'}<br>
                                        <span class="text-muted">→ ${j.valid ? '✅ Valide' : '❌ Invalide'}</span>
                                    </small>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted"><em>Aucune justification</em></p>'}
                    
                    ${data.implications && data.implications.length > 0 ? `
                        <h6 class="mt-3">Implications:</h6>
                        <ul class="list-unstyled">
                            ${data.implications.map(imp => `<li class="text-muted">→ ${imp}</li>`).join('')}
                        </ul>
                    ` : ''}
                    
                    <div class="mt-3 d-grid gap-2">
                        <button class="btn btn-outline-primary btn-sm" onclick="editBelief('${beliefName}')">
                            <i class="fas fa-edit"></i> Éditer
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="removeBelief('${beliefName}')">
                            <i class="fas fa-trash"></i> Supprimer
                        </button>
                    </div>
                </div>
            `;
            
            document.getElementById('belief-details').innerHTML = detailsHtml;
            
        } catch (error) {
            console.error('❌ Erreur détails croyance:', error);
            document.getElementById('belief-details').innerHTML = `
                <div class="text-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    Erreur lors du chargement des détails
                </div>
            `;
        }
    }
    
    /**
     * Efface les détails de croyance
     */
    clearBeliefDetails() {
        document.getElementById('belief-details').innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-mouse-pointer fa-2x mb-2"></i>
                <p>Sélectionnez une croyance<br>dans le graphe</p>
            </div>
        `;
    }
    
    /**
     * Met à jour les statistiques affichées
     */
    updateStatistics(stats = null) {
        if (!stats) {
            // Calcul des statistiques depuis les données actuelles
            const totalBeliefs = this.nodes.length;
            const beliefs = this.nodes.get();
            
            let validCount = 0, invalidCount = 0, unknownCount = 0, nonmonotonicCount = 0;
            
            beliefs.forEach(belief => {
                // Analyser la couleur pour déterminer le statut
                if (belief.color.background === this.colors.valid.background) validCount++;
                else if (belief.color.background === this.colors.invalid.background) invalidCount++;
                else if (belief.color.background === this.colors.nonmonotonic.background) nonmonotonicCount++;
                else unknownCount++;
            });
            
            stats = {
                total_beliefs: totalBeliefs,
                total_justifications: this.edges.length,
                valid_beliefs: validCount,
                invalid_beliefs: invalidCount,
                unknown_beliefs: unknownCount,
                nonmonotonic_beliefs: nonmonotonicCount
            };
        }
        
        // Mise à jour de l'affichage
        document.getElementById('total-beliefs').textContent = stats.total_beliefs || 0;
        document.getElementById('total-justifications').textContent = stats.total_justifications || 0;
        document.getElementById('valid-beliefs').textContent = stats.valid_beliefs || 0;
        document.getElementById('invalid-beliefs').textContent = stats.invalid_beliefs || 0;
        document.getElementById('unknown-beliefs').textContent = stats.unknown_beliefs || 0;
        document.getElementById('nonmonotonic-beliefs').textContent = stats.nonmonotonic_beliefs || 0;
    }
    
    /**
     * Ajoute une entrée au log d'activité
     */
    logActivity(message) {
        const timestamp = new Date().toLocaleTimeString();
        const logHtml = `
            <div class="log-entry">
                <span class="log-timestamp">${timestamp}</span><br>
                <span>${message}</span>
            </div>
        `;
        
        const logContainer = document.getElementById('activity-log');
        if (logContainer) {
            logContainer.insertAdjacentHTML('afterbegin', logHtml);
            
            // Limiter à 50 entrées
            const logs = logContainer.children;
            if (logs.length > 50) {
                logContainer.removeChild(logs[logs.length - 1]);
            }
        }
    }
    
    /**
     * Affiche l'état vide du graphe
     */
    showEmptyState() {
        const container = document.getElementById('network-container');
        if (container) {
            container.innerHTML = `
                <div class="d-flex justify-content-center align-items-center h-100">
                    <div class="text-center text-muted">
                        <i class="fas fa-project-diagram fa-3x mb-3 opacity-50"></i>
                        <h5>Aucune croyance dans cette session</h5>
                        <p>Créez votre première croyance pour commencer</p>
                        <button class="btn btn-primary" onclick="document.getElementById('new-belief').focus()">
                            <i class="fas fa-plus"></i> Créer une croyance
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * Obtient la classe CSS pour le statut d'une croyance
     */
    getStatusClass(beliefData) {
        if (beliefData.non_monotonic) return 'belief-status non-monotonic';
        if (beliefData.valid === true) return 'belief-status justified';
        if (beliefData.valid === false) return 'belief-status unjustified';
        return 'belief-status unknown';
    }
    
    /**
     * Obtient le texte du statut d'une croyance
     */
    getStatusText(beliefData) {
        if (beliefData.non_monotonic) return 'Non-monotonic';
        if (beliefData.valid === true) return 'Valide';
        if (beliefData.valid === false) return 'Invalide';
        return 'Inconnu';
    }
    
    /**
     * Ajuste la vue du réseau
     */
    fitNetwork() {
        if (this.network) {
            this.network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }
    }
    
    /**
     * Active/désactive la physique du réseau
     */
    togglePhysics() {
        if (this.network) {
            this.physicsEnabled = !this.physicsEnabled;
            this.network.setOptions({ physics: { enabled: this.physicsEnabled } });
            
            const button = document.querySelector('button[onclick="togglePhysics()"]');
            if (button) {
                button.innerHTML = this.physicsEnabled ? 
                    '<i class="fas fa-pause"></i>' : 
                    '<i class="fas fa-play"></i>';
            }
            
            this.logActivity(`⚙️ Physique ${this.physicsEnabled ? 'activée' : 'désactivée'}`);
        }
    }
    
    /**
     * Affiche une notification
     */
    showNotification(message, type = 'info') {
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
}

// ============================================================================
// FONCTIONS GLOBALES D'INTERFACE
// ============================================================================

/**
 * Ajoute une nouvelle croyance
 */
async function addBelief() {
    const beliefName = document.getElementById('new-belief').value.trim();
    if (!beliefName) {
        alert('Veuillez saisir un nom de croyance');
        return;
    }
    
    try {
        const response = await fetch('/jtms/api/belief', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                belief_name: beliefName,
                session_id: window.jtmsDashboard?.currentSession || 'global'
            })
        });
        
        if (response.ok) {
            document.getElementById('new-belief').value = '';
            if (window.jtmsDashboard) {
                window.jtmsDashboard.logActivity(`✅ Croyance "${beliefName}" créée`);
                window.jtmsDashboard.showNotification(`Croyance "${beliefName}" créée avec succès`, 'success');
            }
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors de la création');
        }
    } catch (error) {
        console.error('❌ Erreur ajout croyance:', error);
        if (window.jtmsDashboard) {
            window.jtmsDashboard.logActivity(`❌ Erreur: ${error.message}`);
            window.jtmsDashboard.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }
}

/**
 * Ajoute une justification
 */
async function addJustification() {
    const premises = document.getElementById('premises').value.trim();
    const negatives = document.getElementById('negatives').value.trim();
    const conclusion = document.getElementById('conclusion').value.trim();
    
    if (!conclusion) {
        alert('La conclusion est obligatoire');
        return;
    }
    
    try {
        const response = await fetch('/jtms/api/justification', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                in_list: premises ? premises.split(',').map(s => s.trim()) : [],
                out_list: negatives ? negatives.split(',').map(s => s.trim()) : [],
                conclusion: conclusion,
                session_id: window.jtmsDashboard?.currentSession || 'global'
            })
        });
        
        if (response.ok) {
            document.getElementById('premises').value = '';
            document.getElementById('negatives').value = '';
            document.getElementById('conclusion').value = '';
            
            if (window.jtmsDashboard) {
                window.jtmsDashboard.logActivity(`🔗 Justification ajoutée: ${premises || '-'} ⊢ ${conclusion}`);
                window.jtmsDashboard.showNotification('Justification ajoutée avec succès', 'success');
            }
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors de l\'ajout');
        }
    } catch (error) {
        console.error('❌ Erreur ajout justification:', error);
        if (window.jtmsDashboard) {
            window.jtmsDashboard.logActivity(`❌ Erreur: ${error.message}`);
            window.jtmsDashboard.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }
}

/**
 * Change de session
 */
function switchSession() {
    const sessionId = document.getElementById('session-select').value;
    if (window.jtmsDashboard) {
        window.jtmsDashboard.loadSession(sessionId);
    }
}

/**
 * Crée une nouvelle session
 */
async function createSession() {
    const sessionName = document.getElementById('new-session').value.trim();
    if (!sessionName) {
        alert('Veuillez saisir un nom de session');
        return;
    }
    
    try {
        const response = await fetch('/jtms/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionName.toLowerCase().replace(/\s+/g, '_'),
                name: sessionName
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            document.getElementById('new-session').value = '';
            
            // Ajouter à la liste
            const select = document.getElementById('session-select');
            const option = new Option(sessionName, result.session_id);
            select.add(option);
            select.value = result.session_id;
            
            // Charger la nouvelle session
            switchSession();
            
            if (window.jtmsDashboard) {
                window.jtmsDashboard.logActivity(`📁 Session "${sessionName}" créée`);
                window.jtmsDashboard.showNotification(`Session "${sessionName}" créée`, 'success');
            }
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors de la création');
        }
    } catch (error) {
        console.error('❌ Erreur création session:', error);
        if (window.jtmsDashboard) {
            window.jtmsDashboard.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }
}

/**
 * Vérifie la cohérence de la session
 */
async function checkConsistency() {
    const sessionId = window.jtmsDashboard?.currentSession || 'global';
    
    try {
        const response = await fetch(`/jtms/api/consistency/${sessionId}`);
        if (response.ok) {
            const result = await response.json();
            const message = result.is_consistent ? 
                '✅ Système cohérent' : 
                `❌ Incohérences détectées (${result.conflicts?.length || 0})`;
            
            if (window.jtmsDashboard) {
                window.jtmsDashboard.logActivity(message);
                window.jtmsDashboard.showNotification(message, result.is_consistent ? 'success' : 'error');
            }
        }
    } catch (error) {
        console.error('❌ Erreur vérification cohérence:', error);
        if (window.jtmsDashboard) {
            window.jtmsDashboard.showNotification('Erreur lors de la vérification', 'error');
        }
    }
}

/**
 * Exporte les données JTMS en JSON
 */
function exportJTMS() {
    if (window.jtmsDashboard) {
        const sessionId = window.jtmsDashboard.currentSession;
        window.open(`/jtms/api/session/${sessionId}`, '_blank');
        window.jtmsDashboard.logActivity(`📥 Export session ${sessionId}`);
    }
}

/**
 * Réinitialise la session JTMS
 */
function resetJTMS() {
    if (confirm('Êtes-vous sûr de vouloir réinitialiser cette session ?')) {
        if (window.jtmsDashboard) {
            window.jtmsDashboard.nodes.clear();
            window.jtmsDashboard.edges.clear();
            window.jtmsDashboard.updateStatistics();
            window.jtmsDashboard.showEmptyState();
            window.jtmsDashboard.logActivity('🔄 Session réinitialisée');
        }
    }
}

/**
 * Efface le log d'activité
 */
function clearLog() {
    const logContainer = document.getElementById('activity-log');
    if (logContainer) {
        logContainer.innerHTML = `
            <div class="log-entry">
                <span class="log-timestamp">${new Date().toLocaleTimeString()}</span><br>
                <span>🧹 Log effacé</span>
            </div>
        `;
    }
}

/**
 * Ajuste la vue du réseau
 */
function fitNetwork() {
    if (window.jtmsDashboard) {
        window.jtmsDashboard.fitNetwork();
    }
}

/**
 * Active/désactive la physique
 */
function togglePhysics() {
    if (window.jtmsDashboard) {
        window.jtmsDashboard.togglePhysics();
    }
}

/**
 * Sauvegarde la visualisation
 */
function saveVisualization() {
    if (window.jtmsDashboard && window.jtmsDashboard.network) {
        const canvas = window.jtmsDashboard.network.canvas.frame.canvas;
        const link = document.createElement('a');
        link.download = `jtms-graph-${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
        
        window.jtmsDashboard.logActivity('📷 Visualisation sauvegardée');
    }
}

// Export global
window.JTMSDashboard = JTMSDashboard;