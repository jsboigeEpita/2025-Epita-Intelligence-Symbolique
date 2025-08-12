# Commande à exécuter à l'intérieur de l'environnement Conda
$command = "python .\demos\validation_complete_epita.py --integration-test --agent-type explore_only --taxonomy argumentation_analysis/data/argumentum_fallacies_taxonomy.csv"

# Appel du script d'activation en lui passant la commande
# C'est la manière correcte d'utiliser ce script.
.\activate_project_env.ps1 -CommandToRun $command

# Capturer et propager le code de sortie
$exitCode = $LASTEXITCODE
exit $exitCode