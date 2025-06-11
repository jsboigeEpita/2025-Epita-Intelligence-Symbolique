import jpype
import os
import glob
import logging
from fastapi import FastAPI
from .endpoints import router as api_router, framework_router

# --- Gestion du cycle de vie de la JVM ---

def start_jvm():
    """Démarre la JVM avec les JARs nécessaires."""
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
        libs_dir = os.path.join(base_dir, '..', 'abs_arg_dung', 'libs')
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
    if jpype.isJVMStarted():
        logging.info("Arrêt de la JVM.")
        jpype.shutdownJVM()

# --- Application FastAPI ---

app = FastAPI(
    title="Argumentation Analysis API",
    on_startup=[start_jvm],
    on_shutdown=[shutdown_jvm]
)

# Inclure les routeurs
app.include_router(api_router, prefix="/api")
app.include_router(framework_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Argumentation Analysis API. JVM status: " + ("Running" if jpype.isJVMStarted() else "Stopped")}