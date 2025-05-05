# Script de validation des ancres de la table des matières
# Ce script vérifie que toutes les ancres dans la table des matières
# correspondent à des sections existantes dans le fichier de contenu

# Paramètres
param(
    [string]$tocFile = "nouvelle_table_des_matieres.md",
    [string]$contentFile = "nouvelle_section_sujets_projets.md"
)

# Fonction pour extraire les ancres de la table des matières
function Get-TocAnchors {
    param([string]$filePath)
    
    $anchors = @()
    $content = Get-Content $filePath
    
    foreach ($line in $content) {
        if ($line -match '\[.*\]\(#(.*)\)') {
            $anchor = $matches[1]
            $anchors += $anchor
        }
    }
    
    return $anchors
}

# Fonction pour générer les ancres à partir des titres de section
function Get-SectionAnchors {
    param([string]$filePath)
    
    $anchors = @()
    $content = Get-Content $filePath
    
    foreach ($line in $content) {
        # Vérifier si la ligne est un titre (commence par #)
        if ($line -match '^#+\s+(.*)$') {
            $title = $matches[1]
            
            # Convertir le titre en ancre selon les règles de GitHub Markdown
            $anchor = $title.ToLower() -replace '[^\w\s-]', '' -replace '\s+', '-'
            $anchors += $anchor
        }
    }
    
    return $anchors
}

# Fonction pour vérifier si une ancre de la table des matières existe dans les sections
function Test-AnchorExists {
    param(
        [string]$anchor,
        [array]$sectionAnchors
    )
    
    foreach ($sectionAnchor in $sectionAnchors) {
        if ($anchor -eq $sectionAnchor) {
            return $true
        }
    }
    
    return $false
}

# Extraire les ancres de la table des matières
Write-Host "Extraction des ancres de la table des matières..."
$tocAnchors = Get-TocAnchors -filePath $tocFile

# Extraire les ancres des sections du contenu
Write-Host "Extraction des ancres des sections du contenu..."
$sectionAnchors = Get-SectionAnchors -filePath $contentFile

# Vérifier chaque ancre de la table des matières
Write-Host "Vérification des ancres..."
$invalidAnchors = @()

foreach ($anchor in $tocAnchors) {
    if (-not (Test-AnchorExists -anchor $anchor -sectionAnchors $sectionAnchors)) {
        $invalidAnchors += $anchor
    }
}

# Afficher les résultats
Write-Host ""
Write-Host "Résultats de la validation:"
Write-Host "-------------------------"
Write-Host "Total des ancres dans la table des matières: $($tocAnchors.Count)"
Write-Host "Total des sections dans le contenu: $($sectionAnchors.Count)"

if ($invalidAnchors.Count -eq 0) {
    Write-Host "Toutes les ancres sont valides!" -ForegroundColor Green
} else {
    Write-Host "Ancres invalides trouvées: $($invalidAnchors.Count)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Liste des ancres invalides:"
    foreach ($anchor in $invalidAnchors) {
        Write-Host "- $anchor" -ForegroundColor Red
    }
}