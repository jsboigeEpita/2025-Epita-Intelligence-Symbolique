# Demo Soutenance — Script Voix Off

**Duree estimee** : 3-5 minutes
**Format** : Terminal recording (VHS) + narration live
**Scenario** : Politique (`examples/scenarios/politics.txt`)
**Workflow** : light (5 phases, ~15s)

---

## Script Timestamps

### [0:00-0:30] Introduction

> "Bonjour, je vous presente notre systeme d'analyse argumentative multi-agents. Le projet combine intelligence artificielle symbolique et connexionniste pour analyser des discours politiques, detecter les sophismes, formaliser les arguments en logique mathematique, et simuler un vote democratique."
>
> "L'architecture est organisee en 3 niveaux : strategique (orchestration), tactique (coordination entre agents), et operationnel (agents individuels comme Sherlock, Watson, le JTMS, le raisonneur FOL)."

### [0:30-1:15] Pipeline — Lancement

> "On lance le pipeline spectacular sur un scenario politique original — un texte qui n'appartient pas au corpus chiffre. Le pipeline comporte 17 phases dans sa version complete ; ici on utilise le workflow 'light' avec 5 phases pour la demo."
>
> "Les phases sont : extraction des arguments, evaluation de qualite, detection de sophismes, traduction en logique formelle, et synthese."
>
> "Le pipeline est declare en DAG via WorkflowDSL — les phases independantes peuvent tourner en parallele."

### [1:15-2:00] Resultats — Arguments & Sophismes

> "En ~15 secondes, le systeme a extrait 7 arguments et detecte 4 sophismes avec des scores de confiance. La detection est hybride : un reseau neuronal identifie les candidats, puis une taxonomie hierarchique a 8 familles les classifie."
>
> "Par exemple, un 'ad hominem' a 87% de confiance, classe dans la famille Pertinence. Un 'faux dilemme' a 75%, dans la famille Presomption."

### [2:00-2:45] Resultats — Logique Formelle

> "Le systeme traduit les arguments en trois formalismes logiques simultanement : propositionnelle, premier ordre, et modale S5. Les formules sont validees par Tweety, un raisonneur formel en Java."
>
> "Le cadre de Dung construit un graphe d'attaques entre arguments et calcule les extensions semantiques — grounded, preferred, stable. Ici, l'argument c1 est rejete en semantique grounded."

### [2:45-3:30] Interface Gradio

> "Pour la soutenance, on a aussi une interface Gradio qui permet de charger des scenarios pre-construits ou de coller n'importe quel texte. L'analyse s'affiche en onglets : arguments, sophismes, logique formelle, contre-arguments, scores de qualite, et synthese narrative."
>
> "Le Gradio appelle exactement le meme pipeline unifie que le CLI, l'API FastAPI, et le batch runner."

### [3:30-4:15] Pattern Mining — Corpus Reel

> "On a egalement fait tourner le pipeline sur 18 extraits de notre corpus chiffre. Le rapport de pattern mining revele que 'l'illusion de regroupement' est le sophisme le plus frequent, avec 21% des unites analysees. Ce sophisme co-occurre avec 5 autres types, ce qui en fait un hub central du reseau de fallacies."
>
> "On observe aussi que le signal JTMS a 100% de couverture croisee avec les detections informelles — chaque fois qu'un sophisme est detecte, le JTMS produit un signal formel de retraction."

### [4:15-4:45] Conclusion

> "En resume : 17 phases d'analyse, multi-agents avec SK, raisonnement formel avec Tweety, pattern mining sur corpus reel, et une architecture Lego extensible. 2845+ tests, CI verte. Merci, questions ?"

---

## Notes Techniques

- **Scenario utilise** : `examples/scenarios/politics.txt` (public, pas du corpus chiffre)
- **Workflow** : `light` pour la demo (~15s), `spectacular` pour les resultats complets (~45s)
- **Cout** : ~$0.01-0.05 par analyse light
- **Enregistrement** : via `vhs < docs/soutenance/demo_tape.tape` (genere `demo.gif`)
- **Alternative** : screencast OBS + voiceover en post-production
