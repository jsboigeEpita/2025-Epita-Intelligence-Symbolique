# Script pour comparer le rendu avant/après modification du README.md
# Auteur: Roo
# Date: 01/05/2025

# Définition des chemins
$originalReadme = "README.md"
$backupReadme = "README.md.backup"
$originalHtml = "README_original.html"
$modifiedHtml = "README_modified.html"

# Fonction pour générer le rendu HTML avec grip
function Generate-HtmlPreview {
    param (
        [string]$markdownFile,
        [string]$outputHtml
    )
    
    Write-Host "Génération du rendu HTML pour $markdownFile..."
    grip $markdownFile --export $outputHtml
    
    if (Test-Path $outputHtml) {
        Write-Host "Rendu HTML généré avec succès: $outputHtml"
        return $true
    } else {
        Write-Host "Erreur lors de la génération du rendu HTML pour $markdownFile"
        return $false
    }
}

# Fonction pour ouvrir les fichiers HTML dans le navigateur
function Open-HtmlFiles {
    param (
        [string]$file1,
        [string]$file2
    )
    
    if (Test-Path $file1) {
        Start-Process $file1
    } else {
        Write-Host "Le fichier $file1 n'existe pas"
    }
    
    if (Test-Path $file2) {
        Start-Process $file2
    } else {
        Write-Host "Le fichier $file2 n'existe pas"
    }
}

# Menu principal
function Show-Menu {
    Clear-Host
    Write-Host "===== Comparaison du rendu Markdown ====="
    Write-Host "1. Sauvegarder le README.md actuel"
    Write-Host "2. Générer le rendu HTML du README.md original"
    Write-Host "3. Générer le rendu HTML du README.md modifié"
    Write-Host "4. Comparer les rendus HTML (ouvrir dans le navigateur)"
    Write-Host "5. Valider la syntaxe Markdown avec markdownlint"
    Write-Host "6. Quitter"
    Write-Host "========================================"
}

# Boucle principale
$continue = $true
while ($continue) {
    Show-Menu
    $choice = Read-Host "Entrez votre choix (1-6)"
    
    switch ($choice) {
        "1" {
            Write-Host "Sauvegarde du README.md actuel..."
            Copy-Item -Path $originalReadme -Destination $backupReadme -Force
            if (Test-Path $backupReadme) {
                Write-Host "Sauvegarde effectuée avec succès: $backupReadme"
            } else {
                Write-Host "Erreur lors de la sauvegarde du README.md"
            }
            Write-Host "Appuyez sur une touche pour continuer..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "2" {
            if (Test-Path $backupReadme) {
                Generate-HtmlPreview -markdownFile $backupReadme -outputHtml $originalHtml
            } else {
                Write-Host "Veuillez d'abord sauvegarder le README.md actuel (option 1)"
            }
            Write-Host "Appuyez sur une touche pour continuer..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "3" {
            Generate-HtmlPreview -markdownFile $originalReadme -outputHtml $modifiedHtml
            Write-Host "Appuyez sur une touche pour continuer..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "4" {
            if ((Test-Path $originalHtml) -and (Test-Path $modifiedHtml)) {
                Write-Host "Ouverture des rendus HTML dans le navigateur..."
                Open-HtmlFiles -file1 $originalHtml -file2 $modifiedHtml
            } else {
                Write-Host "Veuillez d'abord générer les rendus HTML (options 2 et 3)"
            }
            Write-Host "Appuyez sur une touche pour continuer..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "5" {
            Write-Host "Validation de la syntaxe Markdown avec markdownlint..."
            Write-Host "Validation du README.md original:"
            markdownlint $originalReadme
            
            Write-Host "`nAppuyez sur une touche pour continuer..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        "6" {
            $continue = $false
        }
        default {
            Write-Host "Choix invalide. Veuillez réessayer."
            Write-Host "Appuyez sur une touche pour continuer..."
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    }
}

Write-Host "Script terminé."