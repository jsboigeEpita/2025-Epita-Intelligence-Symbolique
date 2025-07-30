# Script pour trouver les références de test obsolètes dans les fichiers Markdown.

# Obtenir le répertoire racine du projet (le parent du répertoire 'scripts')
$projectRoot = (Get-Item -Path (Join-Path $PSScriptRoot "..")).FullName

# 1. Lister tous les fichiers .md dans le projet
$markdownFiles = Get-ChildItem -Path $projectRoot -Recurse -Filter "*.md"

# 2. Définir le motif regex pour trouver les chemins de test potentiels
$regex = '([a-zA-Z0-9_/\.-]*tests/[a-zA-Z0-9_/\.-]+\.[a-zA-Z]{2,})'

# 3. Parcourir chaque fichier .md
foreach ($file in $markdownFiles) {
    # Utiliser -ErrorAction SilentlyContinue pour ignorer les fichiers qui ne peuvent pas être lus
    $fileContent = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    
    # Rechercher toutes les correspondances dans le contenu du fichier
    $matches = $fileContent | Select-String -Pattern $regex -AllMatches
    
    if ($matches) {
        foreach ($match in $matches.Matches) {
            $referencePath = $match.Groups[1].Value
            
            # Construire le chemin absolu pour la vérification
            $absolutePath = Join-Path -Path $projectRoot -ChildPath $referencePath.Replace('/', '\')
            
            # 4. Vérifier si le fichier référencé existe
            if (-not (Test-Path -Path $absolutePath -PathType Leaf)) {
                # 5. Si le fichier n'existe pas, afficher l'information
                Write-Output "Référence obsolète trouvée :"
                Write-Output "  - Dans le fichier : $($file.FullName)"
                Write-Output "  - Référence       : $($referencePath)"
                Write-Output "--------------------------------------------------"
            }
        }
    }
}