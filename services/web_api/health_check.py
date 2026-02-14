#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification de santé des services
============================================

Vérifie l'état de santé des services backend/frontend avec tests
des endpoints et rapports de statut. Utilise l'infrastructure Python existante.

Usage:
    python services/web_api/health_check.py
    python services/web_api/health_check.py --detailed
    python services/web_api/health_check.py --continuous

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import asyncio
import argparse
import aiohttp
import json
import psutil
from datetime import datetime
from pathlib import Path

# Ajout du chemin racine pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.webapp.process_cleaner import ProcessCleaner

    PROCESS_CLEANER_AVAILABLE = True
except ImportError:
    PROCESS_CLEANER_AVAILABLE = False


def find_processes_by_port(port):
    """Trouve les processus utilisant un port spécifique."""
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            for conn in proc.connections(kind="inet"):
                if conn.laddr.port == port:
                    processes.append(
                        {
                            "pid": proc.pid,
                            "name": proc.name(),
                            "cmdline": " ".join(proc.cmdline()),
                            "cpu_percent": proc.cpu_percent(),
                            "memory_mb": proc.memory_info().rss / 1024 / 1024,
                        }
                    )
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes


async def check_endpoint_health(url, timeout=5):
    """Vérifie la santé d'un endpoint."""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            start_time = asyncio.get_event_loop().time()
            async with session.get(url) as response:
                end_time = asyncio.get_event_loop().time()
                response_time = (end_time - start_time) * 1000

                return {
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "status_code": response.status,
                    "response_time_ms": round(response_time, 2),
                    "content_type": response.headers.get("content-type", "unknown"),
                    "accessible": True,
                }
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "accessible": False,
            "error": f"Timeout après {timeout}s",
        }
    except Exception as e:
        return {"status": "error", "accessible": False, "error": str(e)}


async def check_api_endpoints(base_url):
    """Vérifie plusieurs endpoints d'une API."""
    endpoints = {
        "homepage": "/",
        "status": "/status",
        "analyze": "/analyze",
        "examples": "/api/examples",
    }

    results = {}
    for name, path in endpoints.items():
        url = f"{base_url.rstrip('/')}{path}"
        results[name] = await check_endpoint_health(url)

    return results


async def check_servicemanager_availability():
    """Vérifie la disponibilité du OrchestrationServiceManager."""
    try:
        from argumentation_analysis.orchestration.service_manager import (
            OrchestrationServiceManager,
        )

        return {"available": True, "status": "importable", "error": None}
    except ImportError as e:
        return {"available": False, "status": "import_error", "error": str(e)}
    except Exception as e:
        return {"available": False, "status": "error", "error": str(e)}


async def check_fallacy_analyzers():
    """Vérifie la disponibilité des analyseurs de sophismes."""
    analyzers = {
        "complex_fallacy_analyzer": "argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer.ComplexFallacyAnalyzer",
        "contextual_fallacy_analyzer": "argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer.ContextualFallacyAnalyzer",
    }

    results = {}
    for name, module_path in analyzers.items():
        try:
            module_name, class_name = module_path.rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            results[name] = {"available": True, "status": "importable"}
        except ImportError as e:
            results[name] = {
                "available": False,
                "status": "import_error",
                "error": str(e),
            }
        except Exception as e:
            results[name] = {"available": False, "status": "error", "error": str(e)}

    return results


async def comprehensive_health_check(detailed=False):
    """Exécute un check de santé complet."""
    print("[HEALTH] VÉRIFICATION DE SANTÉ DES SERVICES")
    print("=" * 50)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DATE] Timestamp: {timestamp}")

    # Ports standards à vérifier
    services = {
        "backend_api": {"port": 5000, "name": "Backend API (ServiceManager)"},
        "frontend_react": {"port": 3000, "name": "Frontend React"},
        "simple_interface": {"port": 3000, "name": "Interface Simple Flask"},
        "alt_backend": {"port": 5001, "name": "Backend alternatif"},
        "alt_frontend": {"port": 3001, "name": "Frontend alternatif"},
    }

    health_report = {
        "timestamp": timestamp,
        "services": {},
        "processes": {},
        "dependencies": {},
        "summary": {},
    }

    # 1. Vérification des processus sur les ports
    print("\n[PORT] VÉRIFICATION DES PORTS")
    print("-" * 30)

    active_services = 0
    for service_id, service_info in services.items():
        port = service_info["port"]
        processes = find_processes_by_port(port)

        if processes:
            print(
                f"[OK] Port {port}: {len(processes)} processus actif(s) - {service_info['name']}"
            )
            active_services += 1
            health_report["processes"][service_id] = processes

            if detailed:
                for proc in processes:
                    print(
                        f"   - PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, RAM: {proc['memory_mb']:.1f}MB)"
                    )
        else:
            print(f"[FAIL] Port {port}: Aucun processus - {service_info['name']}")
            health_report["processes"][service_id] = []

    # 2. Tests des endpoints
    print("\n[WEB] TESTS DES ENDPOINTS")
    print("-" * 30)

    for service_id, service_info in services.items():
        if health_report["processes"][service_id]:  # Si processus actif
            port = service_info["port"]
            base_url = f"http://localhost:{port}"

            print(f"[CHECK] Test de {service_info['name']} ({base_url})...")
            endpoints_health = await check_api_endpoints(base_url)
            health_report["services"][service_id] = {
                "base_url": base_url,
                "endpoints": endpoints_health,
            }

            # Résumé des endpoints
            healthy_endpoints = sum(
                1 for ep in endpoints_health.values() if ep.get("status") == "healthy"
            )
            total_endpoints = len(endpoints_health)

            if healthy_endpoints == total_endpoints:
                print(
                    f"   [OK] Tous les endpoints actifs ({healthy_endpoints}/{total_endpoints})"
                )
            elif healthy_endpoints > 0:
                print(
                    f"   ⚠️ Partiellement actif ({healthy_endpoints}/{total_endpoints} endpoints)"
                )
            else:
                print(
                    f"   [FAIL] Aucun endpoint accessible ({healthy_endpoints}/{total_endpoints})"
                )

            if detailed:
                for ep_name, ep_health in endpoints_health.items():
                    status_symbol = (
                        "[OK]" if ep_health.get("status") == "healthy" else "[FAIL]"
                    )
                    response_time = ep_health.get("response_time_ms", "N/A")
                    print(f"     {status_symbol} {ep_name}: {response_time}ms")

    # 3. Vérification des dépendances
    print("\n[TOOLS] VÉRIFICATION DES DÉPENDANCES")
    print("-" * 30)

    # ServiceManager
    sm_health = await check_servicemanager_availability()
    health_report["dependencies"]["service_manager"] = sm_health
    sm_symbol = "[OK]" if sm_health["available"] else "[FAIL]"
    print(
        f"{sm_symbol} OrchestrationServiceManager: {'Disponible' if sm_health['available'] else 'Non disponible'}"
    )

    # Analyseurs de sophismes
    analyzers_health = await check_fallacy_analyzers()
    health_report["dependencies"]["fallacy_analyzers"] = analyzers_health
    available_analyzers = sum(1 for a in analyzers_health.values() if a["available"])
    total_analyzers = len(analyzers_health)
    analyzers_symbol = (
        "[OK]"
        if available_analyzers == total_analyzers
        else "⚠️" if available_analyzers > 0 else "[FAIL]"
    )
    print(
        f"{analyzers_symbol} Analyseurs de sophismes: {available_analyzers}/{total_analyzers} disponibles"
    )

    if detailed:
        for analyzer_name, analyzer_health in analyzers_health.items():
            analyzer_symbol = "[OK]" if analyzer_health["available"] else "[FAIL]"
            print(f"   {analyzer_symbol} {analyzer_name}")

    # 4. Résumé global
    total_services = len([s for s in health_report["processes"].values() if s])
    total_endpoints_healthy = sum(
        sum(1 for ep in service["endpoints"].values() if ep.get("status") == "healthy")
        for service in health_report["services"].values()
    )

    health_report["summary"] = {
        "active_services": total_services,
        "healthy_endpoints": total_endpoints_healthy,
        "service_manager_available": sm_health["available"],
        "fallacy_analyzers_available": available_analyzers,
        "overall_status": (
            "healthy"
            if total_services > 0 and sm_health["available"]
            else "degraded" if total_services > 0 else "critical"
        ),
    }

    print("\n" + "=" * 50)
    print("[STATS] RÉSUMÉ GLOBAL")
    print("=" * 50)
    print(f"[PORT] Services actifs: {total_services}")
    print(f"[WEB] Endpoints fonctionnels: {total_endpoints_healthy}")
    print(
        f"[TOOLS] OrchestrationServiceManager: {'[OK] Disponible' if sm_health['available'] else '[FAIL] Non disponible'}"
    )
    print(f"[CHECK] Analyseurs: {available_analyzers}/{total_analyzers} disponibles")

    overall_status = health_report["summary"]["overall_status"]
    status_symbols = {"healthy": "[GREEN]", "degraded": "[YELLOW]", "critical": "[RED]"}
    print(
        f"[STATUS] État général: {status_symbols.get(overall_status, '[UNKNOWN]')} {overall_status.upper()}"
    )

    return health_report


async def continuous_monitoring(interval=30):
    """Surveillance continue des services."""
    print("[MONITOR] MODE SURVEILLANCE CONTINUE")
    print(f"[STATS] Intervalle: {interval} secondes")
    print("[INFO] Appuyez sur Ctrl+C pour arrêter")
    print("=" * 50)

    try:
        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Vérification...")

            # Check rapide des ports principaux
            ports_to_check = [3000, 5000]
            active_ports = []

            for port in ports_to_check:
                processes = find_processes_by_port(port)
                if processes:
                    active_ports.append(port)

            # Check santé des endpoints actifs
            endpoint_health = {}
            for port in active_ports:
                url = f"http://localhost:{port}"
                health = await check_endpoint_health(url, timeout=3)
                endpoint_health[port] = health["accessible"]

            # Affichage compact
            ports_status = " | ".join(
                [
                    f"Port {port}: {'[OK]' if endpoint_health.get(port, False) else '[FAIL]'}"
                    for port in ports_to_check
                ]
            )

            print(f"[{timestamp}] {ports_status}")

            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print("\n[STOP] Surveillance arrêtée")


async def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Vérification de santé des services backend/frontend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python services/web_api/health_check.py              # Check de base
  python services/web_api/health_check.py --detailed   # Check détaillé
  python services/web_api/health_check.py --continuous # Surveillance continue
        """,
    )

    parser.add_argument(
        "--detailed", action="store_true", help="Affichage détaillé des informations"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Surveillance continue (Ctrl+C pour arrêter)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Intervalle de surveillance en secondes (défaut: 30)",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Sauvegarde le rapport dans un fichier JSON",
    )

    args = parser.parse_args()

    try:
        if args.continuous:
            await continuous_monitoring(args.interval)
        else:
            health_report = await comprehensive_health_check(detailed=args.detailed)

            if args.save_report:
                report_file = (
                    PROJECT_ROOT
                    / "logs"
                    / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                report_file.parent.mkdir(exist_ok=True)
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(health_report, f, indent=2, ensure_ascii=False)
                print(f"\n[FILE] Rapport sauvegardé dans: {report_file}")

            # Code de sortie basé sur l'état général
            overall_status = health_report["summary"]["overall_status"]
            return overall_status in ["healthy", "degraded"]

        return True

    except KeyboardInterrupt:
        print("\n[STOP] Interruption utilisateur")
        return False
    except Exception as e:
        print(f"[FAIL] Erreur critique: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n[END] Script terminé - {'Succès' if success else 'Échec'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[STOP] Interruption finale")
        sys.exit(1)
