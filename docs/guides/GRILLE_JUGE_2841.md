# Grille du juge — campagne #2841 (analyse complète vs zero-shot)

**Origine** : mandat user du 2026-10-27 — « jugez déjà vous-même de ce que vous produisez, en
comparant typiquement à ce que du zero shot produit ou simplement votre intuition sur les
textes ». Le critère d'arrêt « option b » prévoyait que l'user lise la campagne ; il a délégué
la lecture. Ce document est le critère écrit qui remplace son jugement — il doit donc être
**falsifiable**, pas une échelle d'appréciation.

**Ce que cette grille n'est pas** : un juge LLM. `argumentation_analysis/evaluation/judge.py`
note des sorties avec le modèle qui les a produites ; s'en servir ici serait noter le pipeline
avec le pipeline. Le juge, c'est un lecteur qui **cite**. Chaque affirmation ci-dessous doit
être accompagnée d'un extrait des deux textes.

**Producteur du dossier de lecture** : `scripts/dataset/render_campaign_reading_folder.py`
(sortie gitignorée, #2353). Chaque fiche porte ses faits mesurés, les actes I-III et la
synthèse du pipeline **en texte intégral**, puis la réponse zero-shot intégrale.

---

## 1. Ce qu'une fiche permet de juger, et ce qu'elle ne permet pas

| permet | ne permet pas |
|---|---|
| ce que le pipeline **établit** et qu'un lecteur peut vérifier dans le document | la qualité interprétative « absolue » des actes (aucun juge humain externe) |
| ce que le zero-shot dit que le pipeline **manque** | l'exactitude historique des lectures |
| ce que le pipeline **déclare** ne pas avoir couvert | l'effet d'un changement de modèle (mesuré séparément, dossier `_sonnet`) |

Un juge qui conclut autre chose que ces trois axes sort de la grille et doit le dire.

## 2. Les trois listes, par document

Chaque item est **cité** depuis les deux textes. Un item sans citation est un item qui n'existe
pas.

### S — ce que l'analyse complète établit que le zero-shot n'établit pas

Cinq natures, de la plus forte à la plus faible. Nommer la nature à chaque item :

| code | nature | ce qui rend l'item vérifiable |
|---|---|---|
| **S1** | **formel** : un verdict FOL / propositionnel / modal qui **discrimine** (incohérence localisée, théorie rejetée) | le verdict porte sur une théorie reconstruite depuis le texte ; le lecteur peut la refaire |
| **S2** | **structurel** : une exclusion ou acceptation Dung (un argument présent dans `preferred` mais absent de `grounded`, etc.) | l'appartenance à une sémantique est un fait du graphe, pas une opinion |
| **S3** | **convergence** : ≥ 3 méthodes indépendantes nommées qui s'accordent | les méthodes sont nommées et leurs champs d'artefacts sont cités |
| **S4** | **honnêteté** : le pipeline **déclare** une couverture partielle ou une dimension non atteinte | la déclaration est dans le rendu, pas dans une annexe |
| **S5** | **qualité** : une note de vertu qui **discrimine** (au-dessus du seuil faible) | en dessous du seuil, l'axe n'est pas concluable — compter comme nul, jamais comme acquis |

⚠ **S3 n'est pas un surplus par nature.** Une convergence qui porte sur la revendication la
moins étayée du texte est un signal de fragilité, pas de force. Quand les deux se confondent,
l'écrire ; ne pas l'appeler surplus.

⚠ **S5 est le piège mesuré de la campagne** : sur les documents lus, toutes les notes tombent
sous le seuil faible. « L'axe qualité n'est pas concluable » est une **absence**, pas un atout.

### M — ce que le zero-shot dit que l'analyse complète manque ou rate

Deux formes seulement, pour éviter la liste ouverte :

- **M1 — contenu** : une observation sur le document qu'aucune ligne du rendu ne porte.
- **M2 — contresens** : une affirmation du rendu que le document démentit, et que le zero-shot
  lit correctement.

Une différence de **forme** (le zero-shot écrit mieux) n'est pas un M. C'est un fait de style,
consigné à part si répété, jamais compté comme manque.

### D — où l'analyse complète est dégradée, et si le zero-shot couvre ce trou

Reprendre la ligne « actes dégradés » des faits mesurés et les fenêtres de lecture. Deux
questions, une par ligne :

1. quelle dimension n'a pas abouti, et sur quelle part du texte l'axe qui juge a-t-il lu ;
2. le zero-shot, qui lit tout, **couvre-t-il** ce trou — oui / non / il le comble en croyant
   le combler (le cas le plus dangereux : il produit une lecture assurée sur la zone que le
   pipeline a déclarée hors de sa portée).

## 3. Verdict par document — cinq états, pas une note

Un score agrégé masque exactement ce que la campagne doit montrer. Le verdict est un état :

| état | condition | ce qu'il dit |
|---|---|---|
| `PIPELINE_SUPPLIES` | au moins un **S1/S2/S3** vérifié, et **aucun M2** | la machinerie apporte quelque chose qu'un lecteur ne pouvait pas obtenir autrement |
| `PIPELINE_SUPPLIES_WITH_GAP` | au moins un S1/S2/S3, **et** soit un M2, soit un D matériel (l'axe qui juge a lu une minorité du texte) | le surplus est réel mais le lecteur doit être averti |
| `PARITY` | aucun S1/S2/S3 ; le rendu ajoute du détail procédural que le lecteur ne peut pas employer | le coût est payé, le surplus ne l'est pas |
| `ZEROSHOT_WINS` | le zero-shot produit une lecture utilisable et le pipeline n'en produit **aucune**, ou une lecture trompeuse | le pipeline perd sur ce document |
| `BOTH_ABSTAIN` | l'entrée n'est pas analysable et **les deux** le disent | cas sain, aucune conclusion sur le pipeline |

**Propriété anti-applaudissement de cette grille** : elle doit pouvoir renvoyer
`ZEROSHOT_WINS`, `PARITY` et `BOTH_ABSTAIN`, et elle l'a fait dès sa première application (voir
§5). Une grille qui ne rend que `PIPELINE_SUPPLIES` sur un corpus de 49 documents est un
instrument cassé, pas un résultat.

## 4. Agrégation — trois nombres et une phrase

1. **N reader-valid** (quintuplet #2062) sur N tentés — c'est déjà mesuré par la campagne, on
   le reprend, on ne le re-mesure pas.
2. **Répartition des cinq états.** C'est le chiffre qui décide.
3. **Coût par état** : le coût pipeline moyen des documents en `PARITY` contre celui des
   documents en `PIPELINE_SUPPLIES`. Un surplus qui ne se trouve que sur les documents chers
   n'est pas un surplus, c'est une corrélation avec la longueur.
4. **Une phrase de conclusion**, qui doit nommer la nature dominante du surplus (S1, S2, S3,
   S4, S5) — et se taire sur ce que la grille ne mesure pas (§1).

## 5. Première application — deux fiches, lues intégralement

Fait le 2026-10-28, avant d'écrire le reste de cette grille, pour qu'elle ne soit pas une
construction a posteriori. Identifiants opaques ; les noms réels restent dans le dossier de
lecture gitignoré.

| fiche | faits | état | justification citée |
|---|---|---|---|
| `doc_A_01` | 320 car., 0 argument, 1 appel, 0,0005 $ (zero-shot 0,0008 $) | **`ZEROSHOT_WINS`** | le pipeline rend **trois actes absents** et une synthèse absente — la fiche est vide ; le zero-shot identifie le document (« en-tête de compte rendu », « coupé au milieu »), nomme l'organe et la date, et explique pourquoi aucune des neuf rubriques n'est remplissable. Le statut `non_argumentative` était **juste** et coûte le minimum ; c'est le **rendu** qui ne dit rien. |
| `doc_A_08` | 921 car., 6 arguments, 6 sophismes, 132 appels, 357,6 s, 0,0958 $ (zero-shot 0,0021 $, **45×**) | **`PIPELINE_SUPPLIES_WITH_GAP`** | **S3** : « Trois méthodes indépendantes convergent sur ce point » ; **S2** : l'argument le plus condamné est « hors de l'extension acceptée », présent seulement dans `conflict-free` et `naive` ; **S4** : « la lecture de la détection de sophismes ne porte que sur 500 caractères des 921 ». **Gap** : l'axe qualité entier est non concluable (« toutes les notes sont sous le seuil faible »), et deux dimensions déclarées non atteintes. |

Deux enseignements que la grille doit garder :

- **Le défaut de `doc_A_01` n'est pas l'analyse, c'est la restitution.** Un statut correct sans
  rendu ne vaut pas moins qu'un refus expliqué : il vaut moins, parce que le lecteur ne sait
  même pas ce qu'il regarde. C'est un défaut à ouvrir (STOP&REPAIR), pas une limite de la grille.
- **Le surplus mesuré est procédural et autocritique, pas interprétatif.** Sur `doc_A_08`, ce
  que le pipeline ajoute au-dessus du zero-shot, c'est *quelles méthodes s'accordent*, *ce qui
  ne survit pas dans le graphe*, et *sur quelle part du texte il a réellement lu*. Un lecteur
  humain peut employer ces trois choses ; il ne peut pas employer un compte de sophismes que le
  rendu réfute ensuite lui-même.

## 6. Budget et cadence

- Lecture **intégrale** des 8 fiches désignées par `00_LIRE_D_ABORD.md` (les situations
  contrastées du corpus), **extensive** pour les 41 autres (faits + actes + première ligne du
  zero-shot, remontée en lecture intégrale seulement si un S ou un M apparaît).
- Zéro appel LLM pour juger. La lecture est du texte déjà produit.
- Une passe par cycle, restitution sous forme de tableau cité, jamais d'impression générale.

## 7. Mesure de corpus faite **avant** la passe complète — S1 est structurellement absent

`01_tableau_corpus.md` donne, pour les 49 documents, le triplet de verdicts formels
(FOL / propositionnelle / modale). Distribution complète, mesurée le 2026-10-28 :

| triplet | documents |
|---|---|
| `3/3/2` | **48** |
| `0/0/0` | 1 (le seul document `non_argumentative`) |

**48 sur 48 documents `ok` portent le même triplet**, alors que le corpus va de 264 à
2 762 977 caractères et de 4 à 6 013 arguments extraits. Un compte constant sur toute la
population ne peut discriminer aucun document.

Conséquence pour la grille, et c'est la plus lourde : **S1 (surplus formel) n'est pas
disponible au niveau corpus dans cette campagne.** Le triplet est une constante du harnais,
pas un verdict sur le texte — le dossier de lecture le dit déjà à demi-mot (« les talons non
traduits #3123 s'y comptent comme résultats »). Le surplus ne peut donc venir que de **S2**
(exclusion/acception Dung), **S3** (convergence nommée) ou **S4** (couverture déclarée). La
conclusion du §4 doit nommer sa nature parmi ces trois-là.

**Ce que cette mesure n'établit pas, et qu'il ne faut pas lui faire dire.** Elle porte sur le
**nombre**, pas sur le **contenu** : trois verdicts de polarités différentes produiraient le
même triplet. Un document peut donc porter un S1 réel que le tableau ne montre pas — il faut
lire les verdicts eux-mêmes dans les annexes de la fiche. La formulation honnête est : *le
tableau du corpus ne peut pas établir de S1 ; une fiche peut encore en porter un, et c'est à
la lecture de le montrer, citation à l'appui.*

Forme à retenir : c'est un instrument **agrégé** qui révèle un défaut que 49 lectures
individuelles auraient pu manquer, une par une.

## 8. Ce qui, après la §7, reste à mesurer

| axe | état |
|---|---|
| S2 (Dung) | à lire fiche par fiche — présent au moins sur `doc_A_08` |
| S3 (convergence) | à lire fiche par fiche — le seul surplus déjà démontré |
| S4 (honnêteté) | à lire fiche par fiche — présent au moins sur `doc_A_08` |
| S1 (formel) | **indisponible au niveau corpus** ; possible par fiche, à vérifier dans les annexes |
| S5 (qualité) | **mesuré comme absence** sur les documents lus |
| M1 / M2 | à établir par comparaison avec le zero-shot de chaque fiche |
