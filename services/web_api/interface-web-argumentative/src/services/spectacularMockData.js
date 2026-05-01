/**
 * Mock data for the Spectacular Dashboard (32 fields).
 * Matches UnifiedAnalysisState from argumentation_analysis/core/shared_state.py.
 * Used for development before Track 1 delivers real data.
 */

export const MOCK_SPECTACULAR_STATE = {
  // ── Metadata ──
  document_id: 'doc_A',
  workflow: 'standard',
  duration_seconds: 478.8,
  phases_completed: 13,
  phases_total: 13,
  timestamp: '2026-04-24T10:30:00Z',

  // ── Section 1: Extraction ──
  raw_text: '[Extrait du discours source — texte complet masqué pour la démo]',
  raw_text_length: 4231,
  identified_arguments: {
    arg_1: 'Le programme éducatif a permis d\'augmenter le taux de réussite de 15%.',
    arg_2: 'Les enseignants rapportent une meilleure implication des élèves.',
    arg_3: 'Le coût du programme est inférieur aux alternatives existantes.',
    arg_4: 'Des études indépendantes confirment ces résultats dans 3 pays.',
    arg_5: 'Le modèle est transposable à d\'autres niveaux scolaires.',
    arg_6: 'Les résultats à long terme montrent un impact durable sur 5 ans.',
    arg_7: 'Les parents sont satisfaits du programme à 87%.',
    arg_8: 'Le programme réduit les inégalités entre zones urbaines et rurales.',
    arg_9: 'Les critiques portent sur le manque de données comparatives.',
    arg_10: 'L\'investissement initial est rentabilisé en 2 ans.',
    arg_11: 'Le programme est conforme aux normes européennes.',
  },
  extracts: [
    { id: 'ext_1', type: 'fact', text: 'Taux de réussite +15% sur cohorte 2023-2025', source: 'rapport_interne_v3.pdf' },
    { id: 'ext_2', type: 'statistic', text: '87% satisfaction parentale (enquête N=1200)', source: 'enquete_satisfaction.xlsx' },
    { id: 'ext_3', type: 'claim', text: 'Impact durable démontré sur 5 cohortes', source: 'etude_longitudinale.pdf' },
    { id: 'ext_4', type: 'fact', text: 'Coût 30% inférieur à Alternative-B', source: 'audit_couts.pdf' },
    { id: 'ext_5', type: 'testimony', text: 'Enseignant: "Les élèves sont plus engagés"', source: 'entretiens_qualitatifs.docx' },
    { id: 'ext_6', type: 'statistic', text: 'Réduction inégalités urbain/rural: -22%', source: 'rapport_interne_v3.pdf' },
    { id: 'ext_7', type: 'claim', text: 'Transposable à primaire et secondaire', source: 'etude_transposabilite.pdf' },
    { id: 'ext_8', type: 'fact', text: 'ROI atteint en 24 mois (seuil: 36)', source: 'audit_couts.pdf' },
    { id: 'ext_9', type: 'fact', text: '3 pays pilotes: BE, CH, PT', source: 'rapport_europeen.pdf' },
    { id: 'ext_10', type: 'claim', text: 'Conforme normes EU-EDUC-2024', source: 'certificat_conformite.pdf' },
    { id: 'ext_11', type: 'statistic', text: 'Cohorte 2024: 95.2% de validation', source: 'resultats_2024.xlsx' },
    { id: 'ext_12', type: 'fact', text: '250 établissements adoptés en 2025', source: 'rapport_deploiement.pdf' },
    { id: 'ext_13', type: 'claim', text: 'Meilleur score PISA dans les zones adoptantes', source: 'etude_comparative_pisa.pdf' },
    { id: 'ext_14', type: 'testimony', text: 'Inspecteur: "Modèle exemplaire de pédagogie active"', source: 'rapport_inspection.pdf' },
    { id: 'ext_15', type: 'fact', text: 'Budget initial: 2.3M€, budget courant: 1.8M€/an', source: 'audit_couts.pdf' },
  ],

  // ── Section 2: Formal Logic ──
  belief_sets: {
    bs_fol: { logic_type: 'FOL', content: '∀x (Program(x) → Successful(x))\n∃t (Teacher(t) ∧ Reports(t, improvement))' },
    bs_prop: { logic_type: 'Propositional', content: 'P → Q\nQ → R\n∴ P → R' },
    bs_modal: { logic_type: 'Modal', content: '□(Program → Success)\n◇(Criticism → Revision)' },
  },
  query_log: [
    { log_id: 'ql_1', belief_set_id: 'bs_fol', query: 'Program(x) ∧ Successful(x)', raw_result: 'SATISFIABLE', interpreted_result: 'Le programme est associé au succès' },
    { log_id: 'ql_2', belief_set_id: 'bs_prop', query: 'P → R', raw_result: 'VALID', interpreted_result: 'La chaîne d\'implication est valide' },
    { log_id: 'ql_3', belief_set_id: 'bs_modal', query: '◇Criticism', raw_result: 'TRUE_IN_S5', interpreted_result: 'La critique est possible' },
    { log_id: 'ql_4', belief_set_id: 'bs_fol', query: '∀x (Cost(x) < Threshold(x))', raw_result: 'SATISFIABLE', interpreted_result: 'Les coûts sont sous le seuil' },
  ],
  fol_analysis_results: [
    { id: 'fol_1', formula: '∀x (Program(x) → Successful(x))', status: 'verified', sort: 'Program', constants: ['prog_edu_2024'], interpretation: 'Tout programme de ce type conduit au succès' },
    { id: 'fol_2', formula: '∃x (Teacher(x) ∧ Engaged(x))', status: 'verified', sort: 'Teacher', constants: ['teacher_sample'], interpretation: 'Au moins un enseignant est engagé' },
    { id: 'fol_3', formula: 'Cost(prog) < Cost(alternative)', status: 'verified', sort: 'Cost', constants: ['prog_edu_2024', 'alternative_b'], interpretation: 'Coût du programme inférieur' },
    { id: 'fol_4', formula: '∀x (Adopt(x) → Satisfies(x, norm_eu))', status: 'verified', sort: 'Norm', constants: ['norm_eu_2024'], interpretation: 'Conformité aux normes européennes' },
    { id: 'fol_5', formula: 'ROI(prog) ∈ [18, 24] months', status: 'verified', sort: 'Finance', constants: ['roi_period'], interpretation: 'ROI atteint entre 18-24 mois' },
    { id: 'fol_6', formula: '∀x (Zone(x, rural) → Benefit(x))', status: 'verified', sort: 'Zone', constants: ['zone_rural'], interpretation: 'Les zones rurales bénéficient' },
  ],
  propositional_analysis_results: [
    { id: 'prop_1', formula: 'P ∧ Q → R', status: 'tautology', variables: { P: 'program_exists', Q: 'funding_ok', R: 'success' } },
  ],
  modal_analysis_results: [
    { id: 'modal_1', formula: '□(Implementation → Results)', status: 'necessary', modality: 'S5' },
  ],
  nl_to_logic_translations: [
    { id: 'nl_1', natural: 'Le programme fonctionne', formal: 'Successful(prog_edu_2024)', confidence: 0.92 },
    { id: 'nl_2', natural: 'Les enseignants sont satisfaits', formal: 'Satisfied(teacher_sample)', confidence: 0.87 },
    { id: 'nl_3', natural: 'Le coût est raisonnable', formal: 'Cost(prog) < Threshold', confidence: 0.78 },
    { id: 'nl_4', natural: 'Les résultats sont durables', formal: 'Durable(results, 5_years)', confidence: 0.85 },
    { id: 'nl_5', natural: 'Le modèle est transposable', formal: '∃x (Transposable(prog, x))', confidence: 0.72 },
    { id: 'nl_6', natural: 'Les parents approuvent', formal: 'Approve(parents, prog)', confidence: 0.91 },
  ],
  formal_synthesis_reports: [
    { id: 'synth_1', title: 'Synthèse formelle globale', summary: '6 formules FOL vérifiées, 1 tautologie propositionnelle, 1 nécessité modale. Aucune contradiction détectée.', coherence_score: 0.94 },
  ],

  // ── Section 3: Fallacies (3-tier) ──
  identified_fallacies: {
    fall_1: {
      type: 'Ad Hominem',
      family: 'Relevance',
      tier1: 'Ad Hominem',
      tier2: 'Personal Attack',
      tier3: 'Tu Quoque',
      justification: 'L\'auteur est critiqué sur sa moralité plutôt que sur ses arguments.',
      target_argument_id: 'arg_9',
      taxonomy_path: 'Relevance > Ad Hominem > Personal Attack > Tu Quoque',
      severity: 0.7,
    },
    fall_2: {
      type: 'Homme de paille',
      family: 'Relevance',
      tier1: 'Straw Man',
      tier2: 'Distortion',
      tier3: 'Exaggeration',
      justification: 'L\'argument opposé est simplifié à l\'extrême avant d\'être réfuté.',
      target_argument_id: 'arg_3',
      taxonomy_path: 'Relevance > Straw Man > Distortion > Exaggeration',
      severity: 0.5,
    },
    fall_3: {
      type: 'Argument tonal',
      family: 'Emotion',
      tier1: 'Appeal to Emotion',
      tier2: 'Tonal Argument',
      tier3: 'Enthusiasm',
      justification: 'Le ton enthousiaste remplace la justification factuelle.',
      target_argument_id: 'arg_5',
      taxonomy_path: 'Emotion > Appeal to Emotion > Tonal Argument > Enthusiasm',
      severity: 0.3,
    },
  },
  neural_fallacy_scores: [
    { text_segment: 'Ce critique a été condamné pour fraude', family: 'ad_hominem', score: 0.87, model: 'CamemBERT-fallacy-v2' },
    { text_segment: 'Ils veulent détruire tout le système', family: 'straw_man', score: 0.72, model: 'CamemBERT-fallacy-v2' },
  ],

  // ── Section 4: JTMS ──
  jtms_beliefs: {
    b_arg_1: { name: 'arg_1_valid', status: 'VALID', justification: 'extracted_from_source', dependencies: [] },
    b_arg_2: { name: 'arg_2_valid', status: 'VALID', justification: 'teacher_testimony', dependencies: ['b_arg_1'] },
    b_arg_3: { name: 'arg_3_valid', status: 'VALID', justification: 'cost_audit', dependencies: [] },
    b_fall_1: { name: 'fall_1_detected', status: 'VALID', justification: 'fallacy_detector_ad_hominem', dependencies: ['b_arg_9'] },
    b_arg_9: { name: 'arg_9_contested', status: 'VALID', justification: 'critical_review', dependencies: [] },
    b_defeat_1: { name: 'defeat_fall_1_to_arg_9', status: 'VALID', justification: 'fallacy_undermines_credibility', dependencies: ['b_fall_1', 'b_arg_9'] },
    b_retract_1: { name: 'arg_9_retracted', status: 'RETRACTED', justification: 'cascade_from_fall_1', dependencies: ['b_defeat_1'] },
    b_arg_4: { name: 'arg_4_valid', status: 'VALID', justification: 'independent_studies', dependencies: [] },
    b_arg_5: { name: 'arg_5_valid', status: 'VALID', justification: 'transposition_study', dependencies: [] },
    b_arg_6: { name: 'arg_6_valid', status: 'VALID', justification: 'longitudinal_data', dependencies: ['b_arg_1'] },
    b_arg_7: { name: 'arg_7_valid', status: 'VALID', justification: 'parent_survey', dependencies: [] },
    b_arg_8: { name: 'arg_8_valid', status: 'VALID', justification: 'inequality_report', dependencies: ['b_arg_1'] },
    b_arg_10: { name: 'arg_10_valid', status: 'VALID', justification: 'roi_analysis', dependencies: ['b_arg_3'] },
    b_arg_11: { name: 'arg_11_valid', status: 'VALID', justification: 'compliance_check', dependencies: [] },
    b_fall_2: { name: 'fall_2_detected', status: 'VALID', justification: 'fallacy_detector_straw_man', dependencies: ['b_arg_3'] },
    b_defeat_2: { name: 'defeat_fall_2_to_arg_3', status: 'VALID', justification: 'straw_man_undermines', dependencies: ['b_fall_2', 'b_arg_3'] },
    b_fall_3: { name: 'fall_3_detected', status: 'VALID', justification: 'fallacy_detector_tonal', dependencies: ['b_arg_5'] },
    b_defeat_3: { name: 'defeat_fall_3_to_arg_5', status: 'VALID', justification: 'tonal_fallacy_flagged', dependencies: ['b_fall_3', 'b_arg_5'] },
    b_cascade_1: { name: 'cascade_retract_dependent_5', status: 'RETRACTED', justification: 'retraction_cascade_from_fall_3', dependencies: ['b_defeat_3'] },
    b_cascade_2: { name: 'cascade_retract_dependent_6', status: 'RETRACTED', justification: 'retraction_cascade_from_5', dependencies: ['b_cascade_1'] },
    b_cascade_3: { name: 'cascade_retract_dependent_8', status: 'RETRACTED', justification: 'retraction_cascade_from_1', dependencies: ['b_cascade_1'] },
    b_reinforce_1: { name: 'reinforce_arg_4', status: 'VALID', justification: 'independent_validation', dependencies: ['b_arg_4'] },
    b_reinforce_2: { name: 'reinforce_arg_11', status: 'VALID', justification: 'norm_compliance', dependencies: ['b_arg_11'] },
    b_reinforce_3: { name: 'reinforce_overall', status: 'VALID', justification: 'majority_args_valid', dependencies: ['b_reinforce_1', 'b_reinforce_2'] },
  },
  jtms_retraction_chain: [
    { trigger: 'fall_3 (Tonal)', retracted: ['b_cascade_1 (arg_5)', 'b_cascade_2 (arg_6)', 'b_cascade_3 (arg_8)'], depth: 3 },
    { trigger: 'fall_1 (Ad Hominem)', retracted: ['b_retract_1 (arg_9)'], depth: 1 },
  ],

  // ── Section 5: ATMS ──
  atms_contexts: [
    {
      id: 'ctx_A',
      hypothesis: 'Programme efficace',
      beliefs_coherent: ['b_arg_1', 'b_arg_2', 'b_arg_3', 'b_arg_4', 'b_arg_6', 'b_arg_7', 'b_arg_8', 'b_arg_10', 'b_arg_11'],
      beliefs_incoherent: ['b_retract_1', 'b_cascade_1', 'b_cascade_2', 'b_cascade_3'],
      status: 'mostly_consistent',
    },
    {
      id: 'ctx_B',
      hypothesis: 'Programme coûteux',
      beliefs_coherent: ['b_arg_3', 'b_arg_10'],
      beliefs_incoherent: [],
      status: 'consistent',
    },
    {
      id: 'ctx_C',
      hypothesis: 'Résultats contestés',
      beliefs_coherent: ['b_fall_1', 'b_fall_2', 'b_fall_3', 'b_defeat_1', 'b_defeat_2', 'b_defeat_3', 'b_retract_1', 'b_cascade_1', 'b_cascade_2', 'b_cascade_3'],
      beliefs_incoherent: ['b_arg_1', 'b_arg_2', 'b_arg_4'],
      status: 'conflicting',
    },
    {
      id: 'ctx_D',
      hypothesis: 'Modèle transposable',
      beliefs_coherent: ['b_arg_4', 'b_arg_5', 'b_arg_11', 'b_reinforce_1', 'b_reinforce_2', 'b_reinforce_3'],
      beliefs_incoherent: [],
      status: 'consistent',
    },
  ],

  // ── Section 6: Dung ──
  dung_frameworks: {
    framework_1: {
      arguments: ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8'],
      attacks: [
        { from: 'a5', to: 'a1' },
        { from: 'a2', to: 'a3' },
        { from: 'a7', to: 'a4' },
        { from: 'a8', to: 'a6' },
      ],
      extensions: {
        grounded: ['a1', 'a3', 'a4', 'a6'],
        preferred: [['a1', 'a3', 'a4', 'a6'], ['a2', 'a4', 'a5', 'a6']],
        stable: [['a1', 'a3', 'a4', 'a6']],
      },
    },
  },

  // ── Section 7: ASPIC ──
  aspic_results: [
    {
      id: 'aspic_1',
      type: 'structured_argument',
      premises: ['Program(X)', 'Evaluated(X, positive)'],
      conclusion: 'Successful(X)',
      rules_applied: ['rule_effectiveness'],
      defeat_status: 'undefeated',
    },
  ],

  // ── Section 8: Counter-Arguments ──
  counter_arguments: [
    { id: 'ca_1', original_argument: 'arg_1', counter_content: 'Le taux de +15% est calculé sur un échantillon biaisé (volontaires uniquement).', strategy: 'counter-example', score: 0.82 },
    { id: 'ca_2', original_argument: 'arg_5', counter_content: 'La transposabilité n\'est démontrée que dans des contextes similaires, pas dans des systèmes éducatifs fondamentalement différents.', strategy: 'distinction', score: 0.75 },
    { id: 'ca_3', original_argument: 'arg_3', counter_content: 'Si le coût direct est inférieur, les coûts indirects (formation, infrastructure) dépassent les alternatives.', strategy: 'reductio_ad_absurdum', score: 0.68 },
    { id: 'ca_4', original_argument: 'arg_7', counter_content: 'La satisfaction à 87% reflète un biais de sélection: les parents insatisfaits ont quitté le programme.', strategy: 'counter-example', score: 0.71 },
    { id: 'ca_5', original_argument: 'arg_10', counter_content: 'Le ROI de 24 mois ne tient pas compte des coûts récurrents de maintenance.', strategy: 'reformulation', score: 0.65 },
  ],

  // ── Section 9: Debate ──
  debate_transcripts: [
    {
      id: 'debate_1',
      topic: 'Faut-il généraliser le programme éducatif ?',
      agents: [
        { id: 'agent_prop', name: 'Socrate', stance: 'pro' },
        { id: 'agent_opp', name: 'Devil\'s Advocate', stance: 'con' },
      ],
      rounds: [
        { round: 1, argument: { id: 'd_arg_1', text: 'Les résultats sont positifs et reproductibles.', type: 'claim', agent: 'agent_prop', score: 0.85 } },
        { round: 2, argument: { id: 'd_arg_2', text: 'Les résultats sont limités à des contextes favorables.', type: 'attack', agent: 'agent_opp', score: 0.72 } },
        { round: 3, argument: { id: 'd_arg_3', text: 'Les 3 pays pilotes incluent des contextes variés.', type: 'rebuttal', agent: 'agent_prop', score: 0.78 } },
      ],
      outcome: 'balanced',
    },
  ],

  // ── Section 10: Governance ──
  governance_decisions: [
    {
      id: 'gov_1',
      proposal: 'Déploiement national du programme',
      voting_method: 'Borda',
      votes: { pro: 7, con: 3, abstain: 1 },
      result: 'adopted',
      consensus_score: 0.72,
    },
    {
      id: 'gov_2',
      proposal: 'Augmentation budget de 50%',
      voting_method: 'Majorité simple',
      votes: { pro: 5, con: 4, abstain: 2 },
      result: 'adopted',
      consensus_score: 0.55,
    },
  ],

  // ── Section 11: Quality ──
  argument_quality_scores: {
    arg_1: { scores: { clarity: 0.92, coherence: 0.88, relevance: 0.95, sufficiency: 0.78, acceptability: 0.90, effectiveness: 0.85, completeness: 0.82, organization: 0.87, cogency: 0.84 }, overall: 0.87, llm_assessment: 'Argument bien structuré avec données chiffrées. Le taux de 15% est précis mais mérite une source.' },
    arg_3: { scores: { clarity: 0.85, coherence: 0.90, relevance: 0.88, sufficiency: 0.70, acceptability: 0.82, effectiveness: 0.78, completeness: 0.75, organization: 0.85, cogency: 0.80 }, overall: 0.81, llm_assessment: 'Comparaison de coûts pertinente. Manque de détail sur les coûts indirects.' },
    arg_9: { scores: { clarity: 0.65, coherence: 0.60, relevance: 0.72, sufficiency: 0.45, acceptability: 0.55, effectiveness: 0.50, completeness: 0.40, organization: 0.68, cogency: 0.52 }, overall: 0.56, llm_assessment: 'Critique vague sans données comparatives. Affirmation non étayée.' },
  },

  // ── Section 12: Narrative Synthesis ──
  narrative: "L'analyse du document doc_A révèle un plaidoyer structuré en faveur du programme éducatif, appuyé par 11 arguments dont 8 sont formellement validés. L'extraction factuelle produit 15 claims sourcés, tandis que l'analyse FOL confirme 6 formules dont ∀x(Program(x)→Successful(x)). Le JTMS identifie 3 chaînes de rétraction déclenchées par 3 sophismes (Ad Hominem, Homme de paille, Argument tonal), affectant les arguments 5, 6, 8 et 9. Le framework de Dung produit une extension stable de 4 arguments. La qualité moyenne des arguments est de 7.5/10, avec une faiblesse notable sur l'argument 9 (critique non étayée). Le débat contradictoire conclut à un équilibre entre arguments pro et con. Le vote de gouvernance recommande le déploiement (Borda, consensus 72%).",

  // ── Section 13: Tweety Advanced ──
  ranking_results: [
    { id: 'rank_1', method: 'TweetyRanking', result: '[a1, a4, a6, a3, a8, a2, a7, a5]', interpretation: 'a1 est l\'argument le plus accepté' },
  ],
  belief_revision_results: [
    { id: 'br_1', operation: 'contract', formula: 'arg_9_valid', result: 'Consistent after contraction', beliefs_removed: 1 },
  ],
  dialogue_results: [
    { id: 'dlg_1', type: 'persuasion', moves: 5, outcome: 'Proponent wins on arg_1' },
  ],
  probabilistic_results: [
    { id: 'prob_1', query: 'P(Successful|Evidence)', result: 0.87, interpretation: 'Probabilité élevée de succès au vu des preuves' },
  ],
  bipolar_results: [
    { id: 'bip_1', supports: [{ from: 'a4', to: 'a1' }], attacks: [{ from: 'a5', to: 'a1' }], result: 'Support l\'emporte sur attack pour a1' },
  ],

  // ── Section 14: Workflow Metadata ──
  analysis_tasks: { task_1: 'Extraction', task_2: 'Formal Analysis', task_3: 'Fallacy Detection', task_4: 'JTMS', task_5: 'Dung', task_6: 'Quality', task_7: 'Counter-Arguments', task_8: 'Debate', task_9: 'Governance', task_10: 'Synthesis' },
  answers: {
    task_1: { author_agent: 'ExtractAgent', answer_text: '15 extracts identifiés', confidence: 0.90 },
    task_3: { author_agent: 'FallacyDetector', answer_text: '3 sophismes détectés', confidence: 0.85 },
  },
  final_conclusion: 'Le programme éducatif est globalement bénéfique (8/11 arguments valides, 87% quality), malgré 3 sophismes identifiés qui affectent marginalement la crédibilité. Déploiement recommandé avec suivi des coûts indirects.',
  errors: [],

  // ── Workflow execution results ──
  workflow_results: {
    workflow_name: 'standard',
    total_phases: 13,
    completed_phases: 13,
    phase_details: [
      { name: 'extract_facts', duration_s: 12.3, status: 'completed' },
      { name: 'identify_arguments', duration_s: 45.1, status: 'completed' },
      { name: 'detect_fallacies', duration_s: 38.7, status: 'completed' },
      { name: 'evaluate_quality', duration_s: 22.5, status: 'completed' },
      { name: 'generate_counter_arguments', duration_s: 55.2, status: 'completed' },
      { name: 'build_jtms', duration_s: 18.4, status: 'completed' },
      { name: 'compute_dung', duration_s: 15.8, status: 'completed' },
      { name: 'run_aspic', duration_s: 12.1, status: 'completed' },
      { name: 'translate_nl_to_logic', duration_s: 35.6, status: 'completed' },
      { name: 'run_governance', duration_s: 8.3, status: 'completed' },
      { name: 'run_debate', duration_s: 62.1, status: 'completed' },
      { name: 'synthesize', duration_s: 25.4, status: 'completed' },
      { name: 'narrative', duration_s: 10.2, status: 'completed' },
    ],
  },
};

/**
 * Counts how many of the 32 fields are populated (non-empty).
 */
export const getFieldCounts = (state) => {
  const counts = {
    populated: 0,
    total: 32,
    by_section: {},
  };

  const fieldsBySection = {
    'Extraction': ['raw_text', 'identified_arguments', 'extracts'],
    'Formal Logic': ['belief_sets', 'query_log', 'fol_analysis_results', 'propositional_analysis_results', 'modal_analysis_results', 'nl_to_logic_translations', 'formal_synthesis_reports'],
    'Fallacies': ['identified_fallacies', 'neural_fallacy_scores'],
    'JTMS': ['jtms_beliefs', 'jtms_retraction_chain'],
    'ATMS': ['atms_contexts'],
    'Dung': ['dung_frameworks'],
    'ASPIC': ['aspic_results'],
    'Counter-Arguments': ['counter_arguments'],
    'Debate': ['debate_transcripts'],
    'Governance': ['governance_decisions'],
    'Quality': ['argument_quality_scores'],
    'Narrative': ['narrative'],
    'Tweety Advanced': ['ranking_results', 'belief_revision_results', 'dialogue_results', 'probabilistic_results', 'bipolar_results'],
    'Workflow': ['analysis_tasks', 'answers', 'final_conclusion', 'workflow_results'],
  };

  for (const [section, fields] of Object.entries(fieldsBySection)) {
    let sectionPopulated = 0;
    for (const f of fields) {
      const val = state[f];
      const populated = val !== undefined && val !== null && val !== '' &&
        (typeof val !== 'object' || Object.keys(val).length > 0 || Array.isArray(val) ? val.length > 0 : false);
      if (populated) {
        sectionPopulated++;
        counts.populated++;
      }
    }
    counts.by_section[section] = { populated: sectionPopulated, total: fields.length };
  }

  return counts;
};

export default MOCK_SPECTACULAR_STATE;
