import requests
import json

url = "http://localhost:5003/api/analyze"
payload = {"text": "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude fiscale."}
headers = {'Content-Type': 'application/json'}

try:
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP 4xx/5xx
    print("Réponse de l'API:")
    print(response.json())
except requests.exceptions.HTTPError as errh:
    print(f"Erreur HTTP: {errh}")
    print(f"Contenu de la réponse: {response.text}")
except requests.exceptions.ConnectionError as errc:
    print(f"Erreur de Connexion: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"Erreur de Timeout: {errt}")
except requests.exceptions.RequestException as err:
    print(f"Oups: Quelque chose s'est mal passé: {err}")