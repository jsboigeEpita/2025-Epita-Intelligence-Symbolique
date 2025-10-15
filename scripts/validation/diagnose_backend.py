import argumentation_analysis.core.environment

#!/usr/bin/env python3
"""
Diagnostic complet du backend - vérifie processus, ports, logs
"""

import os
import psutil
import subprocess
import requests
from pathlib import Path


def check_processes():
    """Vérifie les processus Python/Uvicorn actifs"""
    print("[PROCESSES] Recherche processus backend...")
    found = []

    for proc in psutil.process_iter(["pid", "name", "cmdline", "status"]):
        try:
            if proc.info["cmdline"]:
                cmdline = " ".join(proc.info["cmdline"])
                if "uvicorn" in cmdline and "argumentation_analysis" in cmdline:
                    found.append(
                        {
                            "pid": proc.info["pid"],
                            "status": proc.info["status"],
                            "cmdline": cmdline[:100],
                        }
                    )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if found:
        print(f"[FOUND] {len(found)} processus backend:")
        for p in found:
            print(f"  PID {p['pid']} ({p['status']}): {p['cmdline']}")
    else:
        print("[NOT_FOUND] Aucun processus backend trouvé")

    return found


def check_ports():
    """Vérifie les ports 5003-5006"""
    print("[PORTS] Vérification ports 5003-5006...")

    for port in [5003, 5004, 5005, 5006]:
        try:
            # Test connexion TCP
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                print(f"  Port {port}: OUVERT")

                # Test HTTP si port ouvert
                try:
                    response = requests.get(
                        f"http://localhost:{port}/api/health", timeout=2
                    )
                    print(f"    HTTP /api/health: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"    HTTP /api/health: ERREUR ({e})")
            else:
                print(f"  Port {port}: FERME")
        except Exception as e:
            print(f"  Port {port}: ERREUR ({e})")


def check_logs():
    """Vérifie les derniers logs Uvicorn"""
    print("[LOGS] Vérification logs récents...")

    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in logs_dir.glob("uvicorn_*.log"):
            try:
                stat = log_file.stat()
                print(
                    f"  {log_file.name}: {stat.st_size} bytes, modifié il y a {(Path().stat().st_mtime - stat.st_mtime):.0f}s"
                )

                # Afficher les dernières lignes si fichier récent
                if stat.st_size > 0:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        if lines:
                            print(f"    Dernière ligne: {lines[-1].strip()}")
            except Exception as e:
                print(f"  {log_file.name}: ERREUR ({e})")
    else:
        print("  Répertoire logs/ non trouvé")


def test_launch_simple():
    """Test de lancement simple pour diagnostic"""
    print("[TEST] Test lancement simple...")

    python_exe = "C:/Users/MYIA/miniconda3/envs/projet-is/python.exe"
    if not os.path.exists(python_exe):
        python_exe = "python"

    cmd = [
        python_exe,
        "-c",
        "import uvicorn; print('Uvicorn available'); from argumentation_analysis.services.web_api.app import app; print('App importable')",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"  Exit code: {result.returncode}")
        if result.stdout:
            print(f"  Stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  Stderr: {result.stderr.strip()}")
    except Exception as e:
        print(f"  ERREUR: {e}")


if __name__ == "__main__":
    print("=== DIAGNOSTIC BACKEND ===")
    check_processes()
    print()
    check_ports()
    print()
    check_logs()
    print()
    test_launch_simple()
    print("=== FIN DIAGNOSTIC ===")
