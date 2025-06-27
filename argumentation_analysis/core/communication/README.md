# Système de Communication

Ce répertoire met en œuvre un système de communication multi-canaux flexible, conçu pour faciliter les interactions entre les différents agents et composants du projet d'analyse d'argumentation.

## Concepts Clés

-   **Message :** L'unité de base de la communication. Chaque message a un type, un expéditeur, un destinataire, une priorité et un contenu.
-   **Channel :** Un canal de communication représente une voie pour l'échange de messages. Le système est conçu pour supporter plusieurs types de canaux (hiérarchiques, de collaboration, de données, etc.).
-   **Interface `Channel` :** Le contrat de base pour tous les canaux est défini dans `channel_interface.py`. Il garantit que tous les canaux, quelle que soit leur implémentation sous-jacente (en mémoire, réseau, etc.), offrent une API cohérente pour envoyer, recevoir et s'abonner à des messages.
-   **`LocalChannel` :** Une implémentation de référence en mémoire de l'interface `Channel`. Elle est principalement utilisée pour les tests et la communication locale simple, mais sert également de modèle pour des implémentations plus complexes.

## Patron de Conception

Le système utilise principalement un patron **Publish/Subscribe (Pub/Sub)**. Les composants peuvent s'abonner (`subscribe`) à un canal pour être notifiés lorsque des messages qui les intéressent sont publiés. Ils peuvent spécifier des `filter_criteria` pour ne recevoir que les messages pertinents.

Ce découplage entre les éditeurs et les abonnés permet une grande flexibilité et une meilleure modularité du système.