# Configuration du Projet d'Analyse Argumentative

Ce répertoire contient les fichiers de configuration nécessaires au fonctionnement du projet d'analyse argumentative.

## Structure du Répertoire

```
config/
├── .env.template
└── README.md
```

## Fichiers de Configuration

### .env.template

Ce fichier est un modèle pour les variables d'environnement utilisées par l'application. Il contient les configurations par défaut qui doivent être personnalisées pour votre environnement local.

#### Contenu du fichier

Le fichier `.env.template` contient les configurations suivantes :

- **Service LLM** : Configuration du service de modèle de langage à utiliser (OpenAI, Azure, etc.)
- **Clés API** : Clés d'accès pour les services externes (OpenAI)
- **Modèle de chat** : Spécification du modèle de chat à utiliser
- **Phrase secrète** : Phrase utilisée pour le chiffrement des configurations sensibles
- **Chemins des répertoires** : Chemins vers les différents répertoires utilisés par l'application

## Utilisation

Pour configurer l'application :

1. **Copier le fichier template** :
   ```bash
   cp argumentation_analysis/config/.env.template .env
   ```

2. **Modifier les valeurs** dans le fichier `.env` selon votre configuration :
   ```bash
   nano .env
   ```

3. **Définir vos clés API** et autres informations sensibles

## Sécurité

- Le fichier `.env` contenant vos clés API et phrases secrètes ne doit **jamais** être commité dans le dépôt Git
- Le fichier `.env` est inclus dans le `.gitignore` pour éviter les commits accidentels
- Les configurations sensibles sont chiffrées avant d'être stockées dans le dépôt

## Intégration avec les Services

Les variables d'environnement définies dans le fichier `.env` sont utilisées par plusieurs services du projet :

- **CryptoService** : Utilise la phrase secrète pour le chiffrement/déchiffrement
- **LLMService** : Utilise les clés API et la configuration du service LLM
- **DefinitionService** : Utilise les chemins des répertoires pour localiser les fichiers de configuration

## Dépannage

Si vous rencontrez des problèmes liés à la configuration :

1. Vérifiez que votre fichier `.env` existe à la racine du projet
2. Assurez-vous que toutes les variables requises sont définies
3. Vérifiez que les chemins des répertoires sont corrects pour votre système
4. Si vous utilisez des services externes, vérifiez que vos clés API sont valides

## Liens vers la Documentation Associée

- [Documentation des Services](../services/README.md)
- [Guide du Développeur](../../docs/guides/guide_developpeur.md)
- [Utilitaires de Configuration](../utils/README.md)