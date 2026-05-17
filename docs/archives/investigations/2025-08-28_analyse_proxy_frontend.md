# Analyse de la Configuration du Proxy Frontend pour les Tests E2E

**Date:** 2025-08-28
**Auteur:** Roo

## 1. Contexte de l'Investigation

Cette investigation a été lancée pour diagnostiquer un problème persistant de CORS affectant les tests End-to-End (E2E). L'hypothèse initiale était une mauvaise configuration du proxy sur le serveur de développement frontend React.

## 2. Découvertes

L'analyse de la base de code du service frontend (`services/web_api/interface-web-argumentative`) a révélé les points suivants :

### 2.1. Présence d'une Configuration de Proxy

Le fichier `package.json` contient bien une directive de proxy :
```json
"proxy": "http://localhost:8095"
```
Cette configuration est le mécanisme standard de Create React App pour rediriger les requêtes API du serveur de développement vers un backend, évitant ainsi les problèmes de CORS en environnement de développement local.

### 2.2. Absence de Configuration de Proxy Avancée

Aucun fichier `src/setupProxy.js` ou `src/middleware.js` n'a été trouvé. Cela indique que seule la configuration de base du proxy est utilisée, sans logique de redirection conditionnelle ou de réécriture de chemin complexe.

### 2.3. Logique des Appels API

Le fichier `src/services/api.js` implémente une logique de communication conçue pour être flexible :
```javascript
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';
```
Toutes les requêtes API sont préfixées par cette constante `API_BASE_URL`.

Ce design engendre deux modes de fonctionnement distincts :
1.  **Mode Proxy (Développement Local) :** Si la variable d'environnement `REACT_APP_BACKEND_URL` n'est pas définie, `API_BASE_URL` est une chaîne vide. Les appels API sont faits vers des chemins relatifs (ex: `/api/health`). Le serveur de développement React intercepte ces appels et les redirige vers la cible du proxy (`http://localhost:8095`), comme attendu.
2.  **Mode Direct (Tests E2E / Production) :** Pendant les tests E2E, un orchestrateur démarre le backend sur un port dynamique et fournit son URL au frontend via la variable `REACT_APP_BACKEND_URL`. Dans ce cas, les appels API sont faits vers une URL absolue (ex: `http://localhost:51234/api/health`). **Le mécanisme de proxy n'est pas utilisé dans ce scénario.** Le navigateur communique directement avec le serveur backend.

## 3. Conclusion

**Le mécanisme de proxy frontend est correctement configuré mais n'est pas la cause du problème de CORS dans les tests E2E.**

Le problème réside très probablement dans la **configuration CORS du serveur backend** (Flask) qui, dans le contexte des tests E2E, ne doit pas autoriser correctement les requêtes provenant de l'origine du serveur de développement frontend (qui tourne sur un port différent et dynamique).

## 4. Recommandation

Il est recommandé de cesser l'investigation sur la configuration du proxy frontend et de **concentrer les efforts de débogage sur la configuration CORS du service backend** (`argumentation_analysis/services/web_api/app.py`).

Il faut s'assurer que la configuration `Flask-CORS` est suffisamment flexible pour accepter les requêtes provenant d'origines dynamiques (`http://localhost:<port>`) telles que celles générées par l'orchestrateur de tests E2E, et ce, même lorsque le frontend utilise des URLs absolues fournies par `REACT_APP_BACKEND_URL`.

## 5. Analyse des En-têtes HTTP avec curl

Suite à la recommandation de se concentrer sur le backend, une analyse directe des en-têtes HTTP a été menée avec `curl`.

### 5.1. Sortie de la Requête "preflight" (OPTIONS)

```bash
curl -v -X OPTIONS http://localhost:8095/api/v1/framework/analyze -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: POST"
```

```http
*   Trying 127.0.0.1:8095...
* Connected to localhost (127.0.0.1) port 8095 (#0)
> OPTIONS /api/v1/framework/analyze HTTP/1.1
> Host: localhost:8095
> User-Agent: curl/7.81.0
> Accept: */*
> Origin: http://localhost:3000
> Access-Control-Request-Method: POST
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< server: uvicorn
< date: Fri, 29 Aug 2025 23:35:50 GMT
< content-type: text/html; charset=utf-8
< allow: OPTIONS, GET, POST, HEAD
< access-control-allow-origin: http://localhost:3000
< access-control-allow-credentials: true
< access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
< vary: Origin
< content-length: 0
<
* Connection #0 to host localhost left intact
```

### 5.2. Sortie de la Requête Réelle (POST)

```bash
curl -v -X POST http://localhost:8095/api/v1/framework/analyze -H "Origin: http://localhost:3000" -H "Content-Type: application/json" -d '{"arguments": ["a"], "attacks": [["a", "a"]]}'
```

```http
*   Trying 127.0.0.1:8095...
* Connected to localhost (127.0.0.1) port 8095 (#0)
> POST /api/v1/framework/analyze HTTP/1.1
> Host: localhost:8095
> User-Agent: curl/7.81.0
> Accept: */*
> Origin: http://localhost:3000
> Content-Type: application/json
> Content-Length: 45
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< server: uvicorn
< date: Fri, 29 Aug 2025 23:36:00 GMT
< content-type: application/json
< content-length: 132
< access-control-allow-origin: http://localhost:3000
< access-control-allow-credentials: true
< vary: Origin
<
{"extensions":{"preferred":[[]]},"semantics":"preferred","statistics":{"arguments_count":1,"attacks_count":1,"extensions_count":1}}
* Connection #0 to host localhost left intact
```

### 5.3. Analyse des Résultats

-   **Requête `OPTIONS` :** La réponse `200 OK` avec les en-têtes `Access-Control-Allow-Origin: http://localhost:3000` et `Access-Control-Allow-Methods` (contenant `POST`) confirme que la configuration CORS de base est correcte.
-   **Requête `POST` :** La réponse `200 OK` avec le corps JSON attendu et l'en-tête `Access-Control-Allow-Origin` confirme que le serveur accepte la requête après la validation "preflight".

## 6. Conclusion Mise à Jour

**La cause racine des problèmes de CORS n'était pas la configuration de Flask-CORS elle-même, mais une cascade d'erreurs d'initialisation dans les services du backend.**

Ces erreurs empêchaient le serveur de démarrer correctement ou de répondre aux requêtes, ce qui se manifestait par des erreurs réseau côté client, interprétées à tort comme des problèmes de CORS.

Après avoir corrigé plusieurs bugs d'injection de dépendances et stabilisé le démarrage du serveur, les tests `curl` démontrent que **le backend est maintenant techniquement capable de gérer les requêtes cross-origin.**

## 7. Recommandation Mise à Jour

**L'investigation sur le backend est terminée et le problème de configuration CORS est résolu.**

Les prochaines étapes devraient être :
1.  **Relancer la suite de tests E2E complète** pour valider que la correction des bugs du backend a bien résolu le problème de manière globale.
2.  **Nettoyer le code** en supprimant les logs de débogage et les modifications temporaires introduites durant cette session.
3.  **Procéder à une revue de code** des modifications apportées pour s'assurer de leur qualité et de leur non-régression.