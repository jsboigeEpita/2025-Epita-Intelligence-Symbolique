import sys
from pathlib import Path
import os
import glob
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints import router as api_router, framework_router

# --- Ajout dynamique de abs_arg_dung au PYTHONPATH ---
# Cela garantit que le service d'analyse peut importer l'agent de l'étudiant.
current_dir = Path(__file__).parent.resolve()
abs_arg_dung_path = current_dir.parent / 'abs_arg_dung'
if str(abs_arg_dung_path) not in sys.path:
    # On l'insère au début pour prioriser ce chemin si nécessaire
    sys.path.insert(0, str(abs_arg_dung_path))
# --- Fin de l'ajout ---

# --- Gestion du cycle de vie de la JVM ---

def start_jvm():
    """Démarre la JVM avec les JARs nécessaires."""
    import jpype
    try:
        logging.info("Tentative de démarrage de la JVM...")
        
        # S'assurer que la JVM n'est pas déjà démarrée
        if jpype.isJVMStarted():
            logging.info("La JVM est déjà démarrée.")
            return

        java_home = os.environ.get('JAVA_HOME', '').strip()
        if not java_home:
            raise RuntimeError("La variable d'environnement JAVA_HOME n'est pas définie.")

        jvm_path = os.path.join(java_home, 'bin', 'server', 'jvm.dll')
        if not os.path.exists(jvm_path):
            jvm_path = os.path.join(java_home, 'lib', 'server', 'libjvm.so')
            if not os.path.exists(jvm_path):
                raise FileNotFoundError(f"JVM non trouvée dans JAVA_HOME: {java_home}")

        # Chemin vers les JARs
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(script_dir) # api/
        # Le script de setup place les JARs dans libs/tweety
        libs_dir = os.path.join(base_dir, '..', 'libs', 'tweety')
        jar_files = glob.glob(os.path.join(libs_dir, '*.jar'))
        if not jar_files:
            raise FileNotFoundError(f"Aucun fichier .jar trouvé dans {libs_dir}")

        classpath = os.pathsep.join(jar_files)
        
        jpype.startJVM(jvm_path, "-ea", f"-Djava.class.path={classpath}")
        logging.info("JVM démarrée avec succès pour l'application.")

    except Exception as e:
        logging.error(f"Erreur critique lors du démarrage de la JVM: {e}")
        # Optionnel: arrêter l'application si la JVM est essentielle
        # raise SystemExit(f"Impossible de démarrer la JVM: {e}")


def shutdown_jvm():
    """Arrête la JVM proprement."""
    import jpype
    if jpype.isJVMStarted():
        logging.info("Arrêt de la JVM.")
        jpype.shutdownJVM()

# --- Application FastAPI ---

app = FastAPI(
    title="Argumentation Analysis API",
    on_startup=[start_jvm],
    on_shutdown=[shutdown_jvm]
)

# --- Configuration CORS ---
# Le frontend est servi sur le port 3001 (ou une autre URL en production),
# le backend sur 5003. Le navigateur bloque les requêtes cross-origin
# par défaut. On autorise explicitement l'origine du frontend.
origins = [
    os.environ.get("FRONTEND_URL", "http://127.0.0.1:3001"),
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Inclure les routeurs
app.include_router(api_router, prefix="/api")
app.include_router(framework_router)

@app.get("/")
async def root():
    import jpype
    return {"message": "Welcome to the Argumentation Analysis API. JVM status: " + ("Running" if jpype.isJVMStarted() else "Stopped")}