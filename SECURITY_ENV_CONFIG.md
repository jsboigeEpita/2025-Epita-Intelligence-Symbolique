# 🔒 Configuration Sécurisée des Variables d'Environnement

## ⚠️ ALERTE DE SÉCURITÉ RÉSOLUE

**Problème détecté** : Le fichier `.env` contenant des clés API sensibles était indexé par Git.

**Actions correctives appliquées** :
1. ✅ Sauvegarde des vraies clés dans `.env.backup.local` (local seulement)
2. ✅ Remplacement du `.env` par un template sécurisé
3. ✅ Suppression de `.env` de l'index Git (`git rm --cached .env`)
4. ✅ Renforcement du `.gitignore` pour éviter toute récidive

## 📋 Configuration Requise

### Étape 1 : Copier vos vraies clés

```bash
# Copiez le template vers votre fichier local
cp .env .env.local

# Éditez .env.local avec vos vraies clés
nano .env.local
```

### Étape 2 : Variables essentielles à configurer

```bash
# OpenAI (OBLIGATOIRE pour le système)
OPENAI_API_KEY=sk-proj-VOTRE_VRAIE_CLE_ICI

# Endpoints locaux (optionnels)
OPENAI_API_KEY_2=VOTRE_CLE_LOCALE_2
OPENAI_API_KEY_3=VOTRE_CLE_LOCALE_3
OPENAI_API_KEY_4=VOTRE_CLE_LOCALE_4
```

### Étape 3 : Utilisation sécurisée

```bash
# Chargez les variables depuis le fichier local
source .env.local

# Ou utilisez python-dotenv
pip install python-dotenv
```

## 🛡️ Règles de Sécurité

### ❌ NE JAMAIS FAIRE :
- Committer des fichiers `.env*` avec de vraies clés
- Partager des clés API dans le code source
- Utiliser des vraies clés dans des fichiers trackés par Git

### ✅ BONNES PRATIQUES :
- Utiliser `.env.local` pour vos clés personnelles
- Utiliser `.env.template` ou `.env.example` pour les exemples
- Garder les vraies clés uniquement en local
- Utiliser des variables d'environnement système en production

## 🔍 Vérification de Sécurité

### Vérifier que .env n'est plus tracké :
```bash
git status .env
# Doit afficher: "Untracked files" ou rien
```

### Vérifier le .gitignore :
```bash
git check-ignore .env .env.local .env.backup.local
# Tous doivent être ignorés
```

## 🚨 En cas de Compromission

Si des clés ont été exposées publiquement :

1. **IMMÉDIAT** : Révoquez toutes les clés compromises
2. **OpenAI** : https://platform.openai.com/api-keys
3. **Générez de nouvelles clés**
4. **Mettez à jour votre `.env.local`**

## 📞 Support

En cas de problème de sécurité, contactez immédiatement l'équipe de développement.

---
**Date de création** : 09/06/2025
**Dernière mise à jour** : 09/06/2025
**Statut** : ✅ Sécurisé