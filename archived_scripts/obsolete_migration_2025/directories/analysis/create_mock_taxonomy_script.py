from pathlib import Path
import pandas as pd # Ajout de l'import pandas pour DataFrame.to_csv et la gestion des NaN
from project_core.utils.file_loaders import load_csv_file

# Définir les chemins
# Le script est supposé être exécuté depuis la racine du projet
project_root = Path(".") 
real_taxonomy_path = project_root / "argumentation_analysis" / "data" / "argumentum_fallacies_taxonomy.csv"
mock_cards_path = project_root / "argumentation_analysis" / "data" / "mock_taxonomy_cards.csv"

# S'assurer que le répertoire de destination existe
mock_cards_path.parent.mkdir(parents=True, exist_ok=True)

# Charger la taxonomie réelle
df_real = load_csv_file(real_taxonomy_path)

if df_real is not None:
    # Filtrer pour les lignes où 'carte' n'est pas vide
    # .notna() gère les NaN. On ajoute aussi une condition pour les chaînes vides si elles existent.
    # S'assurer que la colonne 'carte' existe pour éviter KeyError
    if 'carte' in df_real.columns:
        condition_not_na = df_real['carte'].notna()
        condition_not_empty_str = df_real['carte'].astype(str).str.strip() != '' # Convertit en str, supprime les espaces et vérifie si non vide
        df_cards = df_real[condition_not_na & condition_not_empty_str]

        # Sauvegarder le DataFrame filtré
        try:
            df_cards.to_csv(mock_cards_path, index=False, encoding='utf-8')
            print(f"SUCCESS: Le fichier mock '{mock_cards_path.name}' a été créé avec succès.")
            print(f"INFO: Nombre de lignes dans '{mock_cards_path.name}': {len(df_cards)}")
            print(f"INFO: Fichier sauvegardé à: {mock_cards_path.resolve()}")
            
            # Lire et afficher les 5 premières lignes pour vérification
            try:
                df_check = pd.read_csv(mock_cards_path, encoding='utf-8')
                print("\nINFO: Les 5 premières lignes du fichier créé (en-tête inclus):")
                print(df_check.head().to_string())
            except Exception as e_read:
                print(f"ERROR: Impossible de lire le fichier mock créé pour vérification: {e_read}")

# --- Ajout pour mock_taxonomy_small.csv ---
            mock_small_path = project_root / "argumentation_analysis" / "data" / "mock_taxonomy_small.csv"
            
            # Le répertoire parent (data) est déjà créé par la logique de mock_cards_path
            # mock_small_path.parent.mkdir(parents=True, exist_ok=True) 

            print(f"\nINFO: Début de la création de '{mock_small_path.name}' à partir de '{mock_cards_path.name}'.")
            # Échantillonner à partir de df_cards (qui contient les données de mock_taxonomy_cards.csv)
            # df_cards est disponible ici car nous sommes toujours dans le bloc try principal où df_cards a été créé.
            
            target_sample_size = 20
            if len(df_cards) < target_sample_size:
                df_small = df_cards.copy() # Prendre tout si moins de 20 lignes
                print(f"INFO: Moins de {target_sample_size} lignes dans '{mock_cards_path.name}' ({len(df_cards)} lignes), toutes les lignes seront utilisées pour '{mock_small_path.name}'.")
            else:
                df_small = df_cards.sample(n=target_sample_size, random_state=42)
                print(f"INFO: Échantillon de {len(df_small)} lignes sélectionné pour '{mock_small_path.name}'.")

            # Sauvegarder le DataFrame échantillonné
            try:
                df_small.to_csv(mock_small_path, index=False, encoding='utf-8')
                print(f"SUCCESS: Le fichier mock '{mock_small_path.name}' a été créé avec succès.")
                print(f"INFO: Nombre de lignes dans '{mock_small_path.name}': {len(df_small)}")
                print(f"INFO: Fichier sauvegardé à: {mock_small_path.resolve()}")

                # Lire et afficher les 5 premières lignes pour vérification
                try:
                    df_small_check = pd.read_csv(mock_small_path, encoding='utf-8')
                    print(f"\nINFO: Les 5 premières lignes du fichier '{mock_small_path.name}' (en-tête inclus):")
                    print(df_small_check.head().to_string())
                except Exception as e_read_small:
                    print(f"ERROR: Impossible de lire le fichier mock '{mock_small_path.name}' créé pour vérification: {e_read_small}")
            
            except Exception as e_save_small:
                print(f"ERROR: Échec de la sauvegarde du fichier mock '{mock_small_path.name}': {e_save_small}")
            # --- Fin de l'ajout pour mock_taxonomy_small.csv ---
        except Exception as e_save:
            print(f"ERROR: Échec de la sauvegarde du fichier mock: {e_save}")
            if isinstance(df_real, pd.DataFrame) and 'carte' in df_real.columns:
                 print(f"DEBUG: Type de la colonne 'carte': {df_real['carte'].dtype}")
                 print(f"DEBUG: Exemples de valeurs dans 'carte' (premières 10 non-NaN): {df_real['carte'].dropna().head(10).tolist()}")
            else:
                print("DEBUG: df_real n'est pas un DataFrame ou la colonne 'carte' est manquante avant le filtrage.")

    else:
        print(f"ERROR: La colonne 'carte' n'existe pas dans le fichier {real_taxonomy_path}")
        print(f"DEBUG: Colonnes disponibles: {df_real.columns.tolist()}")
else:
    print(f"ERROR: Échec du chargement du fichier de taxonomie réelle: {real_taxonomy_path}")