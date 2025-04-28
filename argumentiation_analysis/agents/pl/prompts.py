# agents/pl/prompts.py
import logging

# --- Fonctions Sémantiques PLAnalyzer (Prompts V8 avec BNF) ---
prompt_text_to_pl_v8 = """
[Instructions]
Transformez le texte fourni ($input) en un belief set PL.
Respectez **STRICTEMENT** la BNF Tweety ci-dessous. Retournez les formules une par ligne, séparées par '\\n'.
N'utilisez **PAS** '&&' ou '>>'. Utilisez les opérateurs !, ||, =>, <=>, ^^.
Utilisez des noms de propositions courts et significatifs (ex: `renewable_essential`, `high_cost`).

```bnf
FORMULASET ::== FORMULA ( "\\n" FORMULA )*
FORMULA ::== PROPOSITION | "(" FORMULA ")" | FORMULA ">>" FORMULA |
            FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA |
            FORMULA "^^" FORMULA | "!" FORMULA | "+" | "-"
PROPOSITION is a sequence of characters excluding |,&,!,(),=,<,> and whitespace.
(Rappel: N'utilisez PAS '>>', utilisez !, ||, =>, <=> si besoin).

[Texte à Analyser]
{{$input}}
+++++
[Belief Set PL (Syntaxe Tweety Valide, une formule par ligne)]
"""

prompt_gen_pl_queries_v8 = """
[Instructions]
Étant donné un texte original ($input) et un belief set PL ($belief_set), générez 2-3 requêtes PL pertinentes pour vérifier la cohérence ou déduire des informations.
Respectez STRICTEMENT la BNF PL Tweety ci-dessous. Retournez les requêtes une par ligne.
N'utilisez PAS '&&' ou '>>'. Utilisez les opérateurs !, ||, =>, <=>, ^^.
Assurez-vous que les propositions utilisées dans les requêtes existent dans le belief set ou sont des combinaisons logiques de celles-ci.
FORMULA ::== PROPOSITION | "(" FORMULA ")" | FORMULA ">>" FORMULA |
            FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA |
            FORMULA "^^" FORMULA | "!" FORMULA | "+" | "-"
PROPOSITION is a sequence of characters excluding |,&,!,(),=,<,> and whitespace.
(Rappel: N'utilisez PAS '>>').

[Texte Original]
{{$input}}
[Belief Set PL]
{{$belief_set}}
+++++
[Requêtes PL Générées (Syntaxe Tweety Valide, une par ligne)]
"""

prompt_interpret_pl_v8 = """
[Instructions]
Interprétez en langage naturel clair le résultat Tweety formaté ($tweety_result) pour une ou plusieurs requêtes PL ($queries).
Le résultat Tweety pour chaque requête indique si elle est 'ACCEPTED (True)' ou 'REJECTED (False)' ou 'Unknown'.
Basez votre interprétation sur le belief set PL fourni ($belief_set) et le texte original ($input).

Pour chaque requête :

    Rappelez la requête.
    Indiquez si elle est Acceptée, Rejetée ou Inconnue.
    Expliquez pourquoi en vous référant aux formules spécifiques du belief set qui justifient le résultat.
        Si ACCEPTED: Montrez comment la requête découle logiquement des formules du belief set.
        Si REJECTED: Expliquez que la requête N'EST PAS une conséquence logique du belief set (elle n'est pas prouvable), ce qui ne signifie pas forcément qu'elle est fausse dans l'absolu. Mentionnez si elle contredit des formules.
        Si Unknown: Indiquez que le raisonneur n'a pas pu déterminer.

    Reliez l'interprétation au sens du texte original si pertinent.


Générez une interprétation globale concise et facile à comprendre.

[Texte Original]
{{$input}}
[Belief Set PL]
{{$belief_set}}
[Requêtes Testées (une par ligne)]
{{$queries}}
[Résultats Formatés Tweety Agrégés (un résultat par ligne)]
{{$tweety_result}}
+++++
[Interprétation Détaillée en Langage Naturel]
"""

# Log de chargement
logging.getLogger(__name__).debug("Module agents.pl.prompts chargé.")