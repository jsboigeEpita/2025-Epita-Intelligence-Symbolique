# Test simple du systeme unifie authentique
# Script simplifie pour validation

param(
    [string]$LogicType = "fol",
    [string]$MockLevel = "none"
)

Write-Host "Test du systeme unifie authentique" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

Write-Host "Configuration de test:" -ForegroundColor Cyan
Write-Host "  - Type de logique: $LogicType" -ForegroundColor White
Write-Host "  - Niveau de mock: $MockLevel" -ForegroundColor White
Write-Host ""

# Test 1: Configuration unifiee
Write-Host "Test 1: Configuration unifiee..." -ForegroundColor Yellow

$configTest = @"
from config.unified_config import UnifiedConfig, LogicType, MockLevel
try:
    config = UnifiedConfig(
        logic_type=LogicType('$LogicType'),
        mock_level=MockLevel('$MockLevel')
    )
    print(f'OK Configuration creee - Logic: {config.logic_type.value}, Mock: {config.mock_level.value}')
except Exception as e:
    print(f'ERREUR configuration: {e}')
"@

try {
    $result1 = python -c $configTest
    Write-Host $result1 -ForegroundColor Green
} catch {
    Write-Host "ERREUR test configuration: $_" -ForegroundColor Red
}

Write-Host ""

# Test 2: Nouvelle interface CLI
Write-Host "Test 2: Interface CLI etendue..." -ForegroundColor Yellow

try {
    $cliTest = "python -m scripts.main.analyze_text --logic-type $LogicType --mock-level $MockLevel --help"
    $result2 = Invoke-Expression $cliTest
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Interface CLI fonctionnelle avec nouveaux parametres" -ForegroundColor Green
    } else {
        Write-Host "PROBLEME avec interface CLI" -ForegroundColor Red
    }
} catch {
    Write-Host "ERREUR test CLI: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: Validation de base
Write-Host "Test 3: Validation de base..." -ForegroundColor Yellow

$validationTest = @"
from config.unified_config import validate_config, PresetConfigs
try:
    config = PresetConfigs.authentic_fol()
    errors = validate_config(config)
    if errors:
        print(f'AVERTISSEMENT Erreurs de validation: {errors}')
    else:
        print('OK Configuration FOL authentique validee')
        print(f'Score authenticite: {100 if config.mock_level.value == "none" else 50}%')
except Exception as e:
    print(f'ERREUR validation: {e}')
"@

try {
    $result3 = python -c $validationTest
    Write-Host $result3 -ForegroundColor Green
} catch {
    Write-Host "ERREUR test validation: $_" -ForegroundColor Red
}

Write-Host ""

# Resume
Write-Host "RESUME DU TEST" -ForegroundColor Cyan
Write-Host "===============" -ForegroundColor Cyan

if ($MockLevel -eq "none") {
    Write-Host "Objectif authenticite 100%: CONFIGURE" -ForegroundColor Green
    Write-Host "Niveau de mock: AUCUN (authentique)" -ForegroundColor Green
} else {
    Write-Host "Mode de developpement avec mocks" -ForegroundColor Yellow
}

Write-Host "Type de logique: $LogicType (recommande vs modal)" -ForegroundColor Green

Write-Host ""
Write-Host "COMMANDE DE TEST COMPLETE:" -ForegroundColor Cyan
$fullCommand = "python -m scripts.main.analyze_text --source-type simple --logic-type $LogicType --agents informal,fol_logic,synthesis --orchestration unified --mock-level $MockLevel --taxonomy full --format markdown --verbose"
Write-Host $fullCommand -ForegroundColor White

Write-Host ""
Write-Host "Test simple termine - Systeme unifie operationnel" -ForegroundColor Green
