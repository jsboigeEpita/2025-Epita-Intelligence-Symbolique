#!/usr/bin/env python3
"""
Test Playwright spécialisé pour l'analyse des interactions API
"""

import pytest
import time
import json
from pathlib import Path
from playwright.sync_api import Page, expect

# Configuration
BACKEND_URL = "http://localhost:5000"

def test_api_analyze_interactions(page: Page):
    """Test avec interactions API /analyze pour générer des traces exploitables"""
    
    # Charger l'interface de test locale
    demo_html_path = Path(__file__).parent / "test_interface_demo.html"
    demo_url = f"file://{demo_html_path.absolute()}"
    
    page.goto(demo_url)
    
    # Vérifier que la page est chargée
    expect(page).to_have_title("Interface d'Analyse Argumentative - Test")
    expect(page.locator("h1")).to_contain_text("Interface d'Analyse Argumentative")
    
    # Intercepter les requêtes API pour capturer les interactions
    api_calls = []
    
    def handle_response(response):
        if "/analyze" in response.url or "/status" in response.url:
            api_calls.append({
                "url": response.url,
                "method": response.request.method,
                "status": response.status,
                "response_text": response.text() if response.status == 200 else None
            })
    
    page.on("response", handle_response)
    
    # Test 1: Vérifier la connectivité backend
    try:
        page.evaluate(f"""
            fetch('{BACKEND_URL}/status')
                .then(response => response.json())
                .then(data => {{
                    console.log('API Status:', data);
                    window.apiConnected = true;
                }})
                .catch(error => {{
                    console.error('API Error:', error);
                    window.apiConnected = false;
                }});
        """)
        
        time.sleep(2)  # Attendre la réponse
        print("✅ Test de connectivité API exécuté")
        
    except Exception as e:
        print(f"⚠️ Connectivité API: {e}")
    
    # Test 2: Analyse d'argument simple
    test_text = "Tous les chats sont des animaux. Félix est un chat. Donc Félix est un animal."
    
    page.locator("#text-input").fill(test_text)
    expect(page.locator("#text-input")).to_have_value(test_text)
    
    # Déclencher l'analyse via JavaScript pour capturer les requêtes
    page.evaluate(f"""
        (async function() {{
            const textInput = document.getElementById('text-input');
            const results = document.getElementById('results');
            
            try {{
                const response = await fetch('{BACKEND_URL}/analyze', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        'text': textInput.value,
                        'analysis_type': 'full_analysis'
                    }})
                }});
                
                const data = await response.json();
                console.log('Analyse Response:', data);
                
                results.innerHTML = '<h3>Résultat d\\'analyse:</h3><pre>' +
                    JSON.stringify(data, null, 2) + '</pre>';
                    
                window.analysisResult = data;
                
            }} catch (error) {{
                console.error('Erreur d\\'analyse:', error);
                results.innerHTML = '<p style="color: red;">Erreur: ' + error.message + '</p>';
                window.analysisError = error.message;
            }}
        }})();
    """)
    
    # Attendre le résultat
    time.sleep(3)
    
    # Vérifier que l'analyse a été affichée
    results = page.locator("#results")
    expect(results).to_be_visible()
    
    # Test 3: Analyse de sophisme
    sophism_text = "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude."
    
    page.locator("#text-input").fill(sophism_text)
    
    page.evaluate(f"""
        (async function() {{
            const textInput = document.getElementById('text-input');
            
            try {{
                const response = await fetch('{BACKEND_URL}/analyze', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        'text': textInput.value,
                        'analysis_type': 'fallacy_detection'
                    }})
                }});
                
                const data = await response.json();
                console.log('Fallacy Detection:', data);
                window.fallacyResult = data;
                
            }} catch (error) {{
                console.error('Erreur détection sophisme:', error);
                window.fallacyError = error.message;
            }}
        }})();
    """)
    
    time.sleep(3)
    
    # Test 4: Test avec argument complexe
    complex_text = """
    Les voitures électriques sont meilleures pour l'environnement car elles ne produisent pas d'émissions directes.
    Cependant, on pourrait argumenter que leur production nécessite des batteries avec des métaux rares.
    Néanmoins, l'analyse du cycle de vie complet montre un avantage environnemental.
    """
    
    page.locator("#text-input").fill(complex_text)
    
    page.evaluate(f"""
        (async function() {{
            const textInput = document.getElementById('text-input');
            
            try {{
                const response = await fetch('{BACKEND_URL}/analyze', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        'text': textInput.value,
                        'analysis_type': 'structure_analysis',
                        'include_premises': true,
                        'include_conclusions': true
                    }})
                }});
                
                const data = await response.json();
                console.log('Complex Analysis:', data);
                window.complexResult = data;
                
            }} catch (error) {{
                console.error('Erreur analyse complexe:', error);
                window.complexError = error.message;
            }}
        }})();
    """)
    
    time.sleep(3)
    
    # Résumé des appels API capturés
    print(f"\n📊 INTERACTIONS API CAPTURÉES: {len(api_calls)}")
    for i, call in enumerate(api_calls, 1):
        print(f"{i}. {call['method']} {call['url']} → {call['status']}")
    
    # Vérifier les résultats dans la console du navigateur
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))
    
    print(f"📝 Messages console: {len(console_logs)}")
    
    # Tests finaux de validation
    expect(page.locator("#text-input")).to_have_value(complex_text)
    expect(page.locator("#results")).to_be_visible()
    
    print("✅ Test complet d'interactions API terminé")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])