# Tweety First-Order Logic (FOL) BNF

Source: `org-tweetyproject-logics-fol/src/main/java/org/tweetyproject/logics/fol/parser/FolParser.java`

This document contains the official BNF (Backus-Naur Form) for a first-order logic knowledge base as parsed by the TweetyProject library.

## General Structure

A knowledge base (`KB`) is composed of three parts in a specific order:
1.  Sorts Declarations (`SORTSDEC`)
2.  Declarations (`DECLAR`) for predicates and functors.
3.  Formulas (`FORMULAS`)

```
KB ::= SORTSDEC DECLAR FORMULAS
```

## Syntax Details

### Sorts Declaration (`SORTSDEC`)
Defines sorts and the constants belonging to them.

**BNF:**
```
SORTSDEC ::= ( SORTNAME "=" "{" (CONSTANTNAME ("," CONSTANTNAME)*)? "}" "\n" )*
```
-   **Example:**
    ```
    homme = {socrate}
    planete = {terre, mars, jupiter}
    ```

### Declarations (`DECLAR`)
Defines predicates and functors.

**BNF:**
```
DECLAR     ::== (FUNCTORDEC | PREDDEC)*
PREDDEC    ::== "type" "(" PREDICATENAME ("(" SORTNAME ("," SORTNAME)* ")")? ")" "\n"
FUNCTORDEC ::== "type" "(" SORTNAME "=" FUNCTORNAME "(" (SORTNAME ("," SORTNAME)*)? ")" ")" "\n"
```
-   **Predicate Example:**
    ```
    type(EstMortel(homme))
    type(Influence(ecrivain, culture))
    ```

### Formulas (`FORMULAS`)
The logical formulas that constitute the knowledge base. They appear after all declarations.

**BNF:**
```
FORMULAS ::= ( "\n" FORMULA)*
FORMULA  ::= ATOM | "forall" VARIABLENAME ":" "(" FORMULA ")" | "exists" VARIABLENAME ":" "(" FORMULA ")" |
             "(" FORMULA ")" | FORMULA "&&" FORMULA | FORMULA "||" FORMULA | "!" FORMULA | "+" | "-" |
             FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA | FORMULA "==" FORMULA | FORMULA "/==" FORMULA |
             FORMULA "^^" FORMULA
ATOM     ::= PREDICATENAME ("(" TERM ("," TERM)* ")")?
TERM     ::= VARIABLENAME | CONSTANTNAME | FUNCTORNAME "(" (TERM ("," TERM)*)?  ")" 
```

- **Example:**
    ```
    EstMortel(socrate)
    forall X:homme (EstMortel(X))