# 🛠️ CORRECTIONS SPÉCIFIQUES - PROBLÈMES DE TRI ET D'AFFICHAGE

## 📋 RÉSUMÉ DES PROBLÈMES IDENTIFIÉS

1. **Tri chronologique absent** : Les enfants ne sont pas triés par date de création
2. **Troncature trop courte** : 80 caractères insuffisants, perte des préfixes
3. **Position incorrecte de la branche b294b11e** : Apparaît au milieu au lieu d'à la fin

---

## 🔧 CORRECTION 1 : TRI CHRONOLOGIQUE

### Fichier : `get-tree.tool.ts`

#### Ligne 158-162 - Remplacer :
```typescript
const children = childrenIds
    .map(childId => buildTree(childId, depth + 1))
    .filter(child => child !== null);
```

#### Par :
```typescript
const children = childrenIds
    .map(childId => {
        const skeleton = skeletons.find(s => s.taskId === childId);
        return {
            id: childId,
            createdAt: skeleton?.metadata?.createdAt || '1970-01-01T00:00:00.000Z',
            node: buildTree(childId, depth + 1)
        };
    })
    .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
    .map(item => item.node)
    .filter(child => child !== null);
```

---

## 🔧 CORRECTION 2 : AUGMENTATION LIMITE TRONCATURE

### Fichier : `get-tree.tool.ts`

#### Ligne 96 - Remplacer :
```typescript
truncate_instruction = 80,
```

#### Par :
```typescript
truncate_instruction = 160,
```

---

## 🔧 CORRECTION 3 : PRÉSERVATION PRÉFIXES

### Fichier : `format-ascii-tree.ts`

#### Ligne 82-86 - Remplacer :
```typescript
let instruction = node.metadata?.truncatedInstruction || node.title || 'No instruction';
if (instruction.length > truncateInstruction) {
    instruction = instruction.substring(0, truncateInstruction - 3) + '...';
}
```

#### Par :
```typescript
let instruction = node.metadata?.truncatedInstruction || node.title || 'No instruction';
if (instruction.length > truncateInstruction) {
    // Préserver les préfixes markdown/bold
    const prefixMatch = instruction.match(/^(\*{1,2}[^*]*\*{1,2}\s*:\s*)/);
    const prefix = prefixMatch ? prefixMatch[1] : '';
    
    if (prefix.length > 0 && prefix.length < truncateInstruction - 10) {
        // Garder le préfixe et tronquer le reste
        const remainingLength = truncateInstruction - prefix.length - 3;
        instruction = prefix + instruction.substring(prefix.length, prefix.length + remainingLength) + '...';
    } else {
        instruction = instruction.substring(0, truncateInstruction - 3) + '...';
    }
}
```

---

## 🔧 CORRECTION 4 : VALEUR PAR DÉFAUT FORMATAGE

### Fichier : `format-ascii-tree.ts`

#### Ligne 58 - Remplacer :
```typescript
truncateInstruction = 80,
```

#### Par :
```typescript
truncateInstruction = 160,
```

---

## 🎯 RÉSULTATS ATTENDUS

### Après corrections :

1. **Tri chronologique** :
   - `ca4d8f9c` (2025-10-13T09:35:57) apparaîtra AVANT `b294b11e` (2025-10-13T21:09:43)
   - L'ordre sera logique : plus anciennes → plus récentes

2. **Affichage amélioré** :
   - Les préfixes `**mission sddd :**` seront préservés
   - 160 caractères au lieu de 80 pour plus de contexte
   - Troncature intelligente qui respecte la structure markdown

3. **Position correcte de la branche** :
   - Notre branche `b294b11e` apparaîtra à sa position chronologique correcte
   - Plus de "branche au milieu" inattendue

---

## 🧪 TEST DE VALIDATION

### Commande de test :
```typescript
use_mcp_tool("roo-state-manager", "get_task_tree", {
  conversation_id: "fe133888-8f0e-4332-ba73-b8d613597148",
  max_depth: 12,
  include_siblings: true,
  output_format: "ascii-tree",
  truncate_instruction: 160
})
```

### Vérifications à effectuer :
1. ✅ `ca4d8f9c` apparaît avant `b294b11e`
2. ✅ Les instructions font ~160 caractères
3. ✅ Les préfixes markdown sont préservés
4. ✅ L'ordre chronologique est respecté à tous les niveaux

---

## 📊 IMPACT DES CORRECTIONS

| Problème | Correction | Impact |
|----------|------------|---------|
| Tri chronologique absent | Ajout tri par date | 🟢 Élevé |
| Troncature 80 caractères | Augmentation à 160 | 🟢 Moyen |
| Perte préfixes | Algorithme préservatif | 🟢 Moyen |
| Position incorrecte b294b11e | Tri chronologique | 🟢 Élevé |

---

## 🚀 PLAN D'IMPLÉMENTATION

1. **Appliquer les patches** dans l'ordre : 1 → 2 → 3 → 4
2. **Redémarrer le MCP** `roo-state-manager`
3. **Tester avec la commande de validation**
4. **Générer un nouvel arbre** pour comparaison
5. **Valider les corrections** avec les vérifications listées

---

*Document généré le 2025-10-16 - Investigation des problèmes de tri et d'affichage*