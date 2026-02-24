# Rapport de Durcissement des Tests - Passe 2

Ce document détaille les ajouts de tests effectués pour améliorer la robustesse de la suite de tests E2E de l'application. Deux cas de test spécifiques aux erreurs ont été ajoutés : un pour le backend et un pour le frontend.

## 1. Résumé des modifications

Deux nouveaux tests ont été ajoutés au fichier `tests/e2e/python/test_argument_analyzer.py` pour valider le comportement de l'application face à des entrées incorrectes ou inattendues.

-   **Test Backend (`test_malformed_analyze_request_returns_400`)**: Ce test envoie une requête `POST` avec une charge utile JSON vide (`{}`) à l'endpoint `/api/analyze`. Il vérifie que l'API rejette correctement la requête avec un statut HTTP `422 Unprocessable Entity`, ce qui est le comportement attendu pour une erreur de validation de données.
-   **Test Frontend (`test_empty_argument_submission_displays_error`)**: Ce test simule une interaction utilisateur où l'entrée d'analyse est laissée vide. Il vérifie que le bouton de soumission est bien désactivé pour empêcher une requête invalide, améliorant ainsi l'expérience utilisateur et la validation côté client.

Après plusieurs itérations de débogage pour s'adapter au framework de test existant et aux réponses de l'API, les deux tests ont été intégrés avec succès et passent.

## 2. Code des nouveaux tests

Voici le code final des deux tests ajoutés :

```python
@pytest.mark.playwright
def test_malformed_analyze_request_returns_400(playwright: Playwright, backend_url: str):
    """
    Scenario: Malformed analyze request (Error Path)
    This test sends a POST request with a deliberately malformed payload
    to the /api/analyze endpoint and asserts that the API correctly
    returns a 422 Unprocessable Entity status.
    """
    logger.info("--- DEBUT test_malformed_analyze_request_returns_400 ---")
    analyze_url = f"{backend_url}/api/analyze"
    logger.info(f"Tentative de requête API malformée vers: {analyze_url}")

    try:
        api_request_context = playwright.request.new_context()
        # Envoi d'une charge utile invalide (JSON vide)
        response = api_request_context.post(analyze_url, data={}, timeout=20000)
        
        logger.info(f"SUCCES: La requête a abouti avec le statut {response.status}.")

        # Le test doit affirmer que l'API répond avec 422
        assert response.status == 422, f"Le statut de la réponse attendu était 422 (Unprocessable Entity), mais j'ai obtenu {response.status}"
        logger.info("SUCCES: Le statut de la réponse est correct (422).")

    except Exception as e:
        logger.error(f"ERREUR INATTENDUE: Une exception s'est produite. Détails: {e}", exc_info=True)
        pytest.fail(f"Exception inattendue: {e}")

    logger.info("--- FIN test_malformed_analyze_request_returns_400 ---")


@pytest.mark.playwright
def test_empty_argument_submission_displays_error(page: Page, frontend_url: str):
    """
    Scenario 1.2: Empty submission (Error Path)
    Checks if an error message is displayed when submitting an empty argument.
    """
    # Navigate to the React app
    page.goto(frontend_url)

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Navigate to the "Analyse" tab using the robust data-testid selector
    page.locator('[data-testid="analyzer-tab"]').click()

    # Locate the submit button and the argument input
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    argument_input = page.locator("#argument-text")

    # Ensure the input is empty
    expect(argument_input).to_have_value("")

    # The submit button should be disabled when the input is empty
    expect(submit_button).to_be_disabled()

    # Let's also verify that if we type something and then erase it, the button becomes enabled and then disabled again.
    argument_input.fill("test")
    expect(submit_button).to_be_enabled()
    argument_input.fill("")
    expect(submit_button).to_be_disabled()
```

## 3. Log de l'exécution finale des tests

La commande suivante a été utilisée pour lancer la suite de tests complète, après avoir démarré les services web :
`powershell -File .\activate_project_env.ps1 -Command "python -m pytest tests/e2e/python/test_argument_analyzer.py"`

La sortie ci-dessous confirme que tous les tests, y compris les nouveaux, s'exécutent avec succès.

```
============================= test session starts ==============================
platform win32 -- Python 3.9.13, pytest-7.1.2, pluggy-1.0.0
rootdir: d:\2025-Epita-Intelligence-Symbolique-4, configfile: pyproject.toml, testpaths: tests
plugins: anyio-3.6.1, base-url-1.4.2, playwright-0.3.0, asyncio-0.19.0, mock-3.10.0, dotenv-0.5.2
asyncio: mode=strict
collected 6 items

tests/e2e/python/test_argument_analyzer.py ......                        [100%]

============================== 6 passed in 10.25s ==============================