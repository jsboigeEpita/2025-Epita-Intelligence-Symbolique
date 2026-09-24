#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'arrêt de tous les services
===================================

Arrête proprement tous les services backend/frontend avec nettoyage
des processus et ports. Utilise l'infrastructure Python existante.

Usage:
    python services/web_api/stop_all_services.py
    python services/web_api/stop_all_services.py --force

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import asyncio
import argparse
import psutil
import signal
from pathlib import Path

# Ajout du chemin racine pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ports checked when --ports is not given.
STANDARD_PORTS = [3000, 5000, 8000, 8080, 3001, 5001]


def find_processes_by_port(port):
    """Trouve les processus utilisant un port spécifique."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            for conn in proc.connections(kind="inet"):
                if conn.laddr.port == port:
                    processes.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes


def find_webapp_processes():
    """Trouve tous les processus liés aux webapps."""
    webapp_processes = []
    keywords = ["flask", "react-scripts", "node", "npm", "service_manager", "app.py"]

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.cmdline()).lower()
            if any(keyword in cmdline for keyword in keywords):
                # Vérifier si c'est bien lié à notre projet
                if (
                    "EPITA" in cmdline
                    or "epita" in cmdline
                    or "argumentation" in cmdline
                    or "interface" in cmdline
                ):
                    webapp_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return webapp_processes


async def stop_services_gracefully(force=False, ports=None):
    """Arrête les services de manière propre, sur ``ports`` ou ``STANDARD_PORTS``."""
    print("🛑 ARRÊT DE TOUS LES SERVICES")
    print("=" * 50)

    standard_ports = list(ports) if ports else STANDARD_PORTS

    # 1. Recherche des processus par ports
    print("🔍 Recherche des processus sur les ports standards...")
    port_processes = {}
    for port in standard_ports:
        processes = find_processes_by_port(port)
        if processes:
            port_processes[port] = processes
            print(f"   Port {port}: {len(processes)} processus trouvé(s)")

    # 2. Recherche des processus webapp par mots-clés
    print("🔍 Recherche des processus webapp...")
    webapp_processes = find_webapp_processes()
    print(f"   {len(webapp_processes)} processus webapp trouvé(s)")

    # 3. Arrêt des processus par ports
    for port, processes in port_processes.items():
        print(f"🔌 Arrêt des processus sur le port {port}...")
        for proc in processes:
            try:
                if force:
                    print(f"   ⚡ Arrêt forcé du processus {proc.pid} ({proc.name()})")
                    proc.kill()
                else:
                    print(f"   🛑 Arrêt propre du processus {proc.pid} ({proc.name()})")
                    proc.terminate()
                    # Attendre un peu pour l'arrêt propre
                    await asyncio.sleep(2)
                    if proc.is_running():
                        print(f"   ⚡ Arrêt forcé nécessaire pour {proc.pid}")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"   ⚠️ Impossible d'arrêter le processus {proc.pid}: {e}")

    # Arrêt des processus webapp restants
    for proc in webapp_processes:
        if proc.pid not in [
            p.pid for processes in port_processes.values() for p in processes
        ]:
            try:
                if force:
                    print(f"   ⚡ Arrêt forcé webapp {proc.pid} ({proc.name()})")
                    proc.kill()
                else:
                    print(f"   🛑 Arrêt propre webapp {proc.pid} ({proc.name()})")
                    proc.terminate()
                    await asyncio.sleep(1)
                    if proc.is_running():
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"   ⚠️ Impossible d'arrêter le processus webapp {proc.pid}: {e}")

    # 4. Nettoyage des fichiers PID s'ils existent
    print("📄 Nettoyage des fichiers PID...")
    pid_files = [
        PROJECT_ROOT / "logs" / "services_pids.json",
        PROJECT_ROOT / "logs" / "simple_interface_pid.json",
        PROJECT_ROOT / "scripts" / "webapp" / "backend_info.json",
    ]

    for pid_file in pid_files:
        if pid_file.exists():
            try:
                pid_file.unlink()
                print(f"   ✅ Supprimé: {pid_file.name}")
            except Exception as e:
                print(f"   ⚠️ Erreur suppression {pid_file.name}: {e}")

    # 5. Vérification finale
    print("🔍 Vérification finale...")
    remaining_processes = []
    for port in standard_ports:
        processes = find_processes_by_port(port)
        remaining_processes.extend(processes)

    if remaining_processes:
        print(f"⚠️ {len(remaining_processes)} processus encore actifs:")
        for proc in remaining_processes:
            print(f"   - PID {proc.pid}: {proc.name()} (port détecté)")

        if force:
            print("⚡ Arrêt forcé des processus restants...")
            for proc in remaining_processes:
                try:
                    proc.kill()
                    print(f"   ✅ Arrêté: PID {proc.pid}")
                except:
                    pass
    else:
        print("✅ Tous les processus sur les ports standards ont été arrêtés")

    print("\n" + "=" * 50)
    print("🎉 ARRÊT TERMINÉ")
    print("   Tous les services web ont été arrêtés")
    print("=" * 50)


async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Arrêt de tous les services backend/frontend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python services/web_api/stop_all_services.py           # Arrêt propre
  python services/web_api/stop_all_services.py --force   # Arrêt forcé
        """,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Arrêt forcé (SIGKILL) au lieu d'arrêt propre (SIGTERM)",
    )
    parser.add_argument(
        "--ports",
        nargs="+",
        type=int,
        help="Ports spécifiques à nettoyer (défaut: 3000 5000 8000 8080)",
    )

    args = parser.parse_args()

    if args.ports:
        print(f"🎯 Ports spécifiques ciblés: {args.ports}")

    try:
        await stop_services_gracefully(force=args.force, ports=args.ports)
        return True
    except KeyboardInterrupt:
        print("\n🛑 Interruption utilisateur")
        return False
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n🏁 Script terminé - {'Succès' if success else 'Échec'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Interruption finale")
        sys.exit(1)
