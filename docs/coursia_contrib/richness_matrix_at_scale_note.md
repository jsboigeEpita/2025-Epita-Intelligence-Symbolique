# Proposition CoursIA — la matrice de richesse à l'échelle du pipeline réel (#1605)

**Date** : 2026-09-08
**Auteur** : `myia-po-2023:2025-Epita-Intelligence-Symbolique` (worker, dispatch R952)
**Mission** : #1605 — item de DoD restant « Proposition CoursIA rédigée
(proposal-only, PR + validation partenaire, barème privacy CoursIA) ».
**Base** : main `45d825a8`.
**Statut** : **proposition amont** — zéro commit dans `D:\CoursIA`. Le protocole
et l'exemple synthétique sont livrés ici ; la mesure de campagne (po-2025,
artefacts finalisés #2062) a été **reçue le 2026-09-08 avec provenance puis
corrigée en v2**, et intégrée telle quelle en section 5 — un créneau reste
ouvert (E3, confrontation du gate à la prose actuelle). Aucun chiffre n'a été
inventé pour compléter les créneaux.

---

## Résumé exécutif

Le notebook CoursIA `Argument_Analysis_Formal_Richness_Matrix.ipynb`
(candidate C, série `SymbolicAI/Argument_Analysis/`) enseigne les quatre
classes de **verdict** — `substantive` / `honest-absent` / `unavailable` /
`theatre` — sur une démo synthétique de 24 cellules. Le chapitre manquant
de la série est le même instrument appliqué **à l'échelle d'un vrai
pipeline de 40 phases**. La mesure à cette échelle (fil #1605, R755/R757)
a forcé un second axe que la démo ne pouvait pas révéler : le **trajet**
que parcourt chaque sortie — *appel → sortie → lecture → décision*.

Cette note livre, dans l'ordre : le protocole complet du chapitre
(résultats-indépendant), le contrat de vérification par lecteur, l'exemple
synthétique public exécutable, les mesures **historiques** étiquetées et
datées, la mesure de campagne **reçue le 2026-09-08 et corrigée en v2**
(provenance, écarts v1→v2 et limites exactes en section 5 ; un créneau — E3 —
encore ouvert), et le contrat de validation partenaire.

---

## 1. Le protocole du chapitre

### Axe 1 — les quatre classes de verdict (FP-23, conditions sur la sortie)

| classe | condition (lue sur la sortie, jamais sur le câblage) |
|---|---|
| `substantive` | mutation d'état réelle (`count ≥ 1`) **ou** verdict formel produit firsthand par le solveur |
| `honest-absent` | câblée mais vide, **et le vide est déclaré** (fail-loud) — le corpus manque la structure |
| `unavailable` | pas de writer distinct, ou solveur injoignable sur ce corpus |
| `theatre` | verdict affirmé sans décision derrière (`fabricated_true`), ou phase déclarée qui n'écrit rien |

La distinction cruciale est entre `honest-absent` et `theatre` : un échec
honnête dit son vide ; un verdict fabriqué ment. *Wiring ≠ output.*

### Axe 2 — le trajet (apparu à l'échelle ; R755/R757)

| étape | question | preuve |
|---|---|---|
| **appel** | la phase a-t-elle tourné ? | elle figure parmi les phases exécutées du run |
| **sortie** | a-t-elle écrit dans l'état ? | la clé d'état visée est peuplée après le run |
| **lecture** | un lecteur du **chemin de la conclusion** la lit-il ? | un lecteur vivant accède à la clé (énumération des lecteurs, pas des writers) |
| **décision** | ce qui est lu change-t-il un verdict ? | le verdict diffère quand la valeur diffère (substitution) |

La leçon de l'échelle : **une étape atteinte n'implique pas la suivante**.
Trois arrêts intermédiaires mesurés : écrite-jamais-lue (attesté non
mobilisé), lue-hors-chemin (visible sans combler), lue-mais-sans-poids
(« décide sans peser »).

### Règle de composition

`substantive` exige le **trajet complet** et une décision **firsthand**.
Un arrêt précoce n'est pas un échec en soi — c'est la **preuve de
l'arrêt** qui classe : fail-loud déclaré → `honest-absent` ; silence
alors que la phase est déclarée → `theatre` muet ; verdict affirmé sans
étape atteinte → `theatre` fabriquant.

### Contrat de preuve par cellule

Chaque case de la matrice (phase × corpus) est adossée à une preuve
citée, jamais à une intention : fichier:ligne pour le writer, compteur
de snapshot persisté pour la sortie, lecteur nommé pour la lecture,
diff de verdict mesuré pour la décision. Une case sans preuve citée
n'est pas remplie.

---

## 2. Comment un lecteur vérifie une affirmation

| affirmation du chapitre | geste de vérification |
|---|---|
| « cette phase est câblée » | grep du registre des writers (`CAPABILITY_STATE_WRITERS` + écritures directes d'invoke-callables) |
| « cette phase a écrit » | clé d'état peuplée dans le snapshot persisté du run (artefact gitignoré) — `scripts/fp23_measure_unmeasured.py` est l'instrument historique |
| « cette sortie est lue » | énumération des lecteurs **vivants** de la clé, chemin-vers-conclusion distingué des consommateurs hors chemin (export, benchmark) |
| « cette sortie pèse » | test de substitution : verdict calculé avec vs sans la valeur — un verdict invariant sous substitution ne décide rien |
| « ceci est du théâtre » | la sentinelle `fabricated_true` (FP-22/FP-23) ou l'absence d'écriture sous phase déclarée |

La règle transverse, apprise à nos dépens : **un vert qui serait vert de
toute façon ne mesure rien**. Chaque instrument du chapitre (comme chaque
gate du pipeline) porte sa substitution dégénérée qui doit le faire
bouger — cf. l'exemple synthétique, section 3.

---

## 3. L'exemple synthétique public

`richness_journey_synthetic_example.ipynb` (ce répertoire) — exécutable
**sans corpus, sans clé API, sans LLM, sans JVM**. Il dérive la
classification par trajet sur un état synthétique construit avec la
classe d'état de production (`UnifiedAnalysisState`), cinq phases
synthétiques couvrant les archétypes d'arrêt, et quatre substitutions
dont chacune déplace exactement la classification qu'elle doit déplacer :

1. vider une sortie → la phase retombe à l'arrêt *appel* ;
2. ajouter un lecteur sur le chemin → elle monte à *lecture* (et pas plus) ;
3. ajouter le poids → elle atteint *décision* — là où la bande peut le sentir ;
4. la borne : dans un état riche, la même phase reste à *lecture* malgré
   lecteur et poids, parce qu'une **bande-compte** est structurellement
   aveugle à un axe que des axes plus riches saturent déjà. Exprimer
   « cette affirmation-là » exige un gate par axe, pas un seuil de bande.

La substitution (4) a été découverte en écrivant l'exemple : l'assert
initial échouait pour la raison exacte que le vrai pipeline avait
mesurée (PR #1609 : « un compte d'axes ne peut structurellement pas
exprimer cette affirmation-là »). Elle est gardée comme enseignement,
pas corrigée.

**Ce que l'exemple n'est pas** : la mesure. Les noms de phases y sont
synthétiques précisément pour n'affirmer la classe d'aucune phase réelle.

---

## 4. Mesures historiques (étiquetées, datées)

⚠ **HISTORIQUE — mesures du fil #1605, 2026-08-06, base `c806a770`-ère,
c'est-à-dire antérieures à la base actuelle et à la campagne #2062.** Elles
valent comme trace de méthode et comme point de départ ; elles ne décrivent
pas l'état courant du pipeline.
⚠ **#1629 (graphe d'attaque construit par index — lecture sur clé fantôme
`target_argument_id`) est OUVERT à la date de cette note** : ce n'est pas un
correctif livré, contrairement à #1630 (FOL empoisonné) et #1631 (`inferences`
usurpées), clos. Tout constat qui touche `target_argument_id` reste donc une
limite **courante**, pas révolue. La mesure courante (campagne #2062, v2, reçue
le 2026-09-08) est en section 5 — plusieurs constats historiques y sont
confirmés (théâtre/vacuité persistante), d'autres révolus (stakes, FOL).

| date | mesure | résultat headline |
|---|---|---|
| 2026-08-06 (R752) | matrice 40 phases, 3 corpus | 5 phases `théâtre` nommées (`neural_detect`, `text_to_kb`, `kb_to_tweety`, `tweety_interpretation`, `synthesis`) ; 1 `unavailable` structurel (`stakes`) ; FOL indisponible par ParserException sur 2 corpus/3 ; entonnoirs 8→1 vers `add_dung_framework` |
| 2026-08-06 (R754) | substitutions sur le gate de conclusion | 0 phrase bloquée sur la prose réelle des 3 corpus (substitution `REAL`) **et** 0 aussi sous `NO_FORMAL` (les deux axes formels effacés) — le pouvoir du gate sur le registre formel est exactement nul ; corpus_A reste à 0 même sous `NOTHING` (les six axes effacés), les deux autres corpus y perdent 1 phrase (marqueur `fallacies`). Le gate est correct, testé, et sans prise sur le vocabulaire réel (« analyse formelle » vs « logique propositionnelle ») |
| 2026-08-06 (R755) | balayage lecteur des champs de bundles | 5 champs à zéro lecteur dont 2 honnêtement redondants ; `counters_total` : 8 artefacts/8 au-dessus du plafond d'énumération, le plus riche vu depuis 14 % du matériel |
| 2026-08-06 (R757) | matrice trajet, 37 phases d'analyse | C (mobilisées) = 27 dont 4 via le saut indirect `deep_synthesis` ; B (attestées non mobilisées) = 2 ; A (n'atteignent pas la conclusion) = 8 ; zéro phase n'écrit rien |
| 2026-08-06 (R757, suite qualitative) | relecture des artefacts contre les sources | ~4 composants porteurs ; ~12 « tournent, se déclarent complétés, ne décident rien » ; causes racines ouvertes #1629 (graphe par index), #1630 (FOL empoisonné), #1631 (`inferences` usurpées) |

Le détail chiffré et les preuves citées vivent dans le fil de l'issue
#1605 (commentaires R752–R757) — cette note référence sans dupliquer.

---

## 5. Mesure de campagne — reçue le 2026-09-08 (po-2025, #2062), **corrigée en v2**

**Provenance** : campagne #2062, base `f95b7af2`, modèle `openai/gpt-5.6-luna`
(`--max-chars 0`), 49 dumps / 47 ok (2 non-ok : 1 non-argumentatif, 1
`llm_unparseable-json` classé non-déterminisme LLM), mesure read-only sans
nouveau run LLM. Livrée par po-2025 en **v1** puis **corrigée en v2** (message
privé du 2026-09-08, PJ `phase_matrix_1605_v2.json` +
`rules_and_evidence_1605_v2.md`). La présente section intègre la **v2** ;
les écarts v1→v2 sont signalés au fil du texte. Les chiffres ci-dessous sont
**reçus tels quels** — aucune interpolation.

### Le point transversal, et la limite exacte de la v1

La v1 comptait **« 33 substantive »** — un compte de **classe de verdict**
(Axe 1 : la clé d'état canonique a été écrite). Cela ne démontre **pas** le
trajet end-to-end : une phase peut écrire sa sortie et ne jamais la voir
reprise en conclusion. La v2 sépare donc **trois étages**, jamais fusionnés
(anti-pendule #1605) :

| étage | question | instrument |
|---|---|---|
| **1. production** | la clé d'état canonique a-t-elle été écrite ? | sondage direct des dumps — 39 phases, statut global 1826 completed / 7 failed / 0 skipped |
| **2. décision-solveur** | le verdict d'axe se lit-il « décidé » ou « disponible » ? | colonne Valeur de la restitution (`appendix.py` tri-state décidé/disponible/indisponible) |
| **3. reprise-en-conclusion** | l'Acte III a-t-il réellement *lu* la dimension ? | colonne Mobilisation |

**Lecture des étages 2+3, sur les 47 ok** — c'est ici que la limite se révèle :
seuls **FOL / PL / Modal** sont à la fois **décidés** et **mobilisés** → apport
**end-to-end établi** pour ces trois axes. dung / aspic / bipolaire / revision
sont **disponible** (flag de présence : `appendix.py` émet « disponible » si la
clé est présente, ce n'est pas une décision de solveur) mais **mobilisés** :
présents et cités, sans décision discrétionnaire derrière.
**`synthese_formelle` (47/47) et `synthese_narrative` (46/47) sont produites
mais NON mobilisées** — le cas « production sans reprise en conclusion », que la
colonne Mobilisation atteste littéralement. **« 33 substantive » ne décrit donc
que l'étage 1** ; l'apport à la conclusion n'est établi (décidé + mobilisé) que
pour **FOL/PL/Modal**.

### Écarts v1 → v2 (classes d'Axe 1 corrigées)

| phase | v1 | v2 | pourquoi |
|---|---|---|---|
| `neural_detect` | théâtre | **zéro mesuré, non-théâtre** | le log de passe dit « completed using 'self_hosted_fallacy_detector' (1.61s) » : l'inférence a **réellement tourné** et rendu 0 détection ; `_write_camembert_to_state` n'écrit `neural_fallacy_scores` que si `output.detections` est non vide → zéro **mesuré** (a tourné, rien trouvé), pas « la phase n'a pas tourné ». Leçon : un conteneur vide ne prouve pas l'absence d'inférence — il faut le log + le service + le seuil d'écriture |
| `setaf_reasoning` | substantive à-qualifier | **perte de structure** | `attacks_submitted` non-nul (jusqu'à 25) mais `attacks=0` (46/46) : le conteneur binaire `add_dung_framework` perd les attaques collectives ; registre `evaluated` 29/46 — le solveur a tourné, la structure ne survit pas |
| `weighted_reasoning` | honnête-absent | honnête-absent (**confirmé**) | même mécanique, mais registre `evaluated_empty` 32 + `degraded` 35/46 et **le gate le nomme à l'Acte III** (« force pondérée non évaluée », 35 WARN) — l'absence est dite |
| `aba_reasoning` | substantive | **perte de structure non vérifiable** | n'expose pas de champ `attacks_submitted`, args fixes 3, att=0 (46/46) — une éventuelle perte d'attaques collectives est **invisible** au conteneur ; impossible de trancher depuis le dump. Cas le plus dangereux |
| `delp_reasoning` | théâtre | vacuité (**confirmé**) | framework **vide** (0 arg, 0 att, 47/47) → extension calculée sur vide = vacuité |
| `text_to_kb` / `kb_to_tweety` / `tweety_interpretation` | théâtre | théâtre (**confirmé**) | aucun `invoke callable` (log « component … has no invoke callable, output None »), clé d'état absente 47/47 |
| `dung_extensions` | substantive | **réconcilié : non uniforme** | framework présent **43/47** ; **4 = `verification_unavailable`** (absent **nommé**, honnête-absent : 6cf07ed6_ext1/ext3, a798a020, c7464ef5) — dénominateur réconcilié, pas un manque |

### Créneaux

| créneau | valeur **v2** |
|---|---|
| E1 — matrice verdict | **39 phases** (le workflow a évolué depuis la base R752 — ne pas figer « 40 » ; la population mesurée de cette époque n'a pas `synthesis`/`sat_solving`). Classes d'Axe 1 **corrigées** (cf. tableau ci-dessus) ; **0 unavailable par construction = conventionnel** : conséquence du câblage de `stakes` (corrigé depuis R752, peuplé 47/47) — « zéro » dit qu'aucun axe n'est structurellement hors d'atteinte, **pas** que chaque axe décide |
| E2 — entonnoir de structure | le discriminant est `attacks_submitted` (soumis par le solveur) vs `attacks` (ce qui **survit** au conteneur binaire) : setaf = perte de structure ; weighted = honnête-absent nommé ; ABA = perte invisible (pas de champ soumission) ; delp = vacuité ; `social_af` = substantive (attaques non-nulles 30/47, = soumises) ; `verification_grounded` (dung) = attaques non-nulles sur 29/43, zéro-attaques 14/43 |
| E3 — gate vs prose **actuelle** | **OUVERT** — la livraison couvre la matrice de phases, pas le rejeu des substitutions du gate contre la prose courante. L'inertie R754 reste une mesure historique tant que ce créneau n'est pas rempli |
| E4 — phases corrigées depuis R757 | `stakes` **corrigé** (unavailable par construction → câblée, 47/47 ; plus aucun unavailable par construction) ; FOL **décide firsthand 47/47** (11 incohérents / 36 cohérents, EProver — l'époque ParserException de R752 est révolue sur cette base ; #1630 CLOSED) ; #1631 CLOSED ; **#1629 OUVERT** (graphe par index — cf. section 4) ; contamination d'axe à l'écriture **persistante** : `dl_reasoning` range son verdict en prose dans le conteneur FOL (`fol_1 = "DL: Knowledge base is consistent."`, 47/47) — reçu tel quel ; #1609 a corrigé la **lecture** d'axe (un invité ne crédite plus l'axe hôte), la cohabitation au niveau conteneur reste mesurée telle quelle |

### Dénominateurs — réconciliés explicitement

- **Population** : 39 phases × 47 ok (n_dumps 49, 2 non-ok). Le statut global
  1826 completed / 7 failed / 0 skipped s'entend sur 47 ok ; les 7 failed = 1
  phase échouée sur ≤7 docs, dominés par `deep_synthesis` (1 timeout pilote) +
  `72e063ff` (`llm_unparseable-json`, non-déterminisme re-ok sur #1894).
- **Clé d'état écrite** : `stage1_production` donne un key_hit par phase —
  47 pour la quasi-totalité, **46** pour les phases absentes sur 1 doc
  (ranking, aspic, belief_revision, deep_synthesis, setaf, weighted, aba),
  **43** pour `dung_extensions`. La différence 46 vs 47 = 1 doc où la phase
  n'a pas tourné ; 43 vs 47 = les 4 `verification_unavailable`, réconciliés.
- **`40` vs `39`** : différence de **population** (l'ancien workflow avait
  `synthesis`/`sat_solving`), pas un artefact de comptage des `stakes` — qui
  sont une **correction**, pas un ajout.

La partie empirique absente ne sera pas déclarée livrée : sans E3, la
confrontation gate↔prose reste un créneau ouvert, et le chapitre l'énonce.

---

## 6. Validation partenaire attendue

Côté CoursIA, la validation naturelle du chapitre :

1. **Reproductibilité** : l'instrument tourne dans le contexte de la série
   (entrée par l'`Executor`, batch Papermill/MCP) sans dépendance corpus.
2. **Les dents** : les substitutions de l'exemple synthétique font bouger
   la classification — le même geste que l'invariant anti-théâtre du
   notebook `Formal_Richness_Matrix` (sa cellule « sentinelle
   `fabricated_true` »), étendu au trajet.
3. **Barème privacy CoursIA** (plus strict que le nôtre) : entrées
   synthétiques publiques uniquement, aucun contenu de corpus, IDs
   opaques sur toute surface indexée.
4. **La discipline historique/pending voyage avec le chapitre** : un
   chapitre qui enseigne l'instrument ne peut pas introduire subrepticement
   des chiffres non datés — chaque nombre porte sa date et sa base, ou il
   n'entre pas.

---

## 7. Anti-pendules

- **Ne pas retirer les phases qui ne décident pas.** Une phase
  `honest-absent` correctement étiquetée est un succès de la matrice,
  pas un échec du pipeline (mandat #1605).
- **Ne pas ajouter de formalisme pour faire du chiffre.** Ce qui manque
  n'est pas un solveur de plus, c'est le compte-rendu honnête de ceux
  qui sont là.
- **Pas de score composite** : « 62 % substantive » masque exactement ce
  que la matrice expose. Les deux axes restent lisibles séparément.
- **`substantive` (étage 1 — la sortie est écrite) ≠ « mobilisé » (étage 3 —
  repris en conclusion)** : le compte de classe est une vue de la production,
  pas du trajet. Sur la campagne #2062 (section 5), seuls FOL/PL/Modal sont
  établis end-to-end (décidés **et** mobilisés) ; les synthèses sont produites
  mais non mobilisées. Un compte « substantive » seul ne valide aucun trajet.
- **Historique ≠ courant** : les mesures R752–R757 sont datées et
  périmées par les correctifs ultérieurs ; elles ne se présentent jamais
  comme l'état présent.
- **Ne pas élargir les marqueurs pour attraper la prose** (leçon R754) :
  quand l'instrument n'atteint pas son objet, on change ce que l'objet
  doit déclarer, pas ce que le filtre attrape.

---

## 8. Liens

- Issue #1605 — corps (mandat utilisateur 2026-08-06) et commentaires
  R751–R757 (mesures historiques citées en section 4)
- PR #1609 — gate de conclusion par axe + invités DL/CL/QBF (merged)
- PR #1614 — lecteur des motifs de dégradation persistés (merged)
- `docs/reports/FP5_FORMAL_RICHNESS_MATRIX.md` (FP-5 #1196) et
  `scripts/fp23_measure_unmeasured.py` (FP-23 #1250) — l'instrument
  historique des quatre classes
- `docs/coursia_contrib/richness_journey_synthetic_example.ipynb` —
  l'exemple synthétique public (section 3)
- `docs/coursia_contrib/restitution_evidential_roles.ipynb` — le sibling
  de la même veine (rôles évidentiels Actes II/III, sans corpus)
- CoursIA : `MyIA.AI.Notebooks/SymbolicAI/Argument_Analysis/Argument_Analysis_Formal_Richness_Matrix.ipynb`
  (la cible du chapitre manquant) · campagne #2062 (artefacts, gitignorés) ·
  mesure **v2** de po-2025 : `phase_matrix_1605_v2.json` +
  `rules_and_evidence_1605_v2.md` (section 5)

🤖 Co-Authored-By: Claude (claude-sonnet-5) <noreply@anthropic.com>
