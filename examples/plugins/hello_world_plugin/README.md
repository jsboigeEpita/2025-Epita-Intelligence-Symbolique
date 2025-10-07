# Hello World Plugin - Exemple Pédagogique

## 🎯 Objectif

Plugin minimaliste démontrant la structure de base d'un plugin pour le système d'analyse argumentative.

Ce plugin sert de **template de référence** pour comprendre :
- La structure minimale d'un plugin
- Le format de configuration (`plugin.yaml`)
- L'implémentation basique d'un plugin fonctionnel

## 📁 Structure

```
hello_world_plugin/
├── README.md          # Ce fichier
├── main.py            # Logique du plugin
└── plugin.yaml        # Configuration du plugin
```

## 🚀 Utilisation

### Pour Apprendre
1. Examinez `plugin.yaml` pour comprendre la structure de configuration
2. Étudiez `main.py` pour voir l'implémentation minimale
3. Utilisez ce template comme base pour créer vos propres plugins

### Pour Développer
```python
# Copiez ce plugin comme point de départ
cp -r examples/plugins/hello_world_plugin plugins/mon_nouveau_plugin
cd plugins/mon_nouveau_plugin
# Modifiez main.py et plugin.yaml selon vos besoins
```

## 📚 Documentation Complète

Pour plus d'informations sur le système de plugins :
- Documentation principale : [`docs/`](../../../docs/)
- Plugins opérationnels : [`plugins/`](../../../plugins/)
- Autres exemples : [`examples/`](../../)

## ⚠️ Note Importante

Ce plugin est **à but pédagogique uniquement**. Pour les plugins de production, consultez :
- `plugins/AnalysisToolsPlugin/` - Outils d'analyse avancés
- `plugins/FallacyWorkflow/` - Workflow de détection de sophismes
- `plugins/GuidingPlugin/` - Plugin de guidage utilisateur

---

**Type** : Exemple pédagogique  
**Statut** : Stable (référence)  
**Mainteneur** : Équipe Projet