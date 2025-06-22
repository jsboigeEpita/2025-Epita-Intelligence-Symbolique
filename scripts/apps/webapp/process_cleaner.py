#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process Cleaner - Gestionnaire de nettoyage des processus d'application web
===========================================================================

Nettoie proprement tous les processus liés à l'application web.

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import sys
import time
import logging
import psutil
from typing import List, Dict, Set, Any
from pathlib import Path

class ProcessCleaner:
    """
    Gestionnaire de nettoyage des processus d'application web
    
    Fonctionnalités :
    - Détection processus Python/Node liés à l'app
    - Arrêt progressif (TERM puis KILL)
    - Libération des ports
    - Nettoyage fichiers temporaires
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        # Patterns de processus à nettoyer
        self.process_patterns = [
            'app.py',
            'web_api',
            'serve',
            'flask',
            'react-scripts',
            'webpack',
            'npm start'
        ]
        
        # Ports utilisés par l'application
        self.webapp_ports = [5003, 5004, 5005, 5006, 3000]
        
        # Extensions de processus
        self.process_names = ['python', 'python.exe', 'node', 'node.exe', 'npm', 'npm.cmd']
    
    async def cleanup_webapp_processes(self):
        """Nettoie tous les processus liés à l'application web"""
        self.logger.info("[CLEAN] Debut nettoyage processus application web")
        
        try:
            # 1. Identification des processus
            webapp_processes = self._find_webapp_processes()
            
            if not webapp_processes:
                self.logger.info("Aucun processus d'application web trouvé")
                return
            
            self.logger.info(f"Processus trouvés: {len(webapp_processes)}")
            
            # 2. Arrêt progressif
            await self._terminate_processes_gracefully(webapp_processes)
            
            # 3. Vérification et force kill si nécessaire
            await self._force_kill_remaining_processes()
            
            # 4. Libération des ports
            await self._check_port_liberation()
            
            # 5. Nettoyage fichiers temporaires
            await self._cleanup_temp_files()
            
            self.logger.info("[OK] Nettoyage processus terminé")
            
        except Exception as e:
            self.logger.error(f"Erreur nettoyage processus: {e}")
    
    def _find_webapp_processes(self) -> List[psutil.Process]:
        """Trouve tous les processus liés à l'application web"""
        webapp_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    
                    # Vérification par nom de processus
                    if proc_info['name'] and any(name in proc_info['name'].lower()
                                               for name in self.process_names):
                        
                        # Vérification par ligne de commande
                        if proc_info['cmdline']:
                            cmdline = ' '.join(proc_info['cmdline']).lower()
                            
                            # Exclure les processus de test Playwright du nettoyage précoce
                            if 'playwright' in cmdline:
                               continue

                            if any(pattern in cmdline for pattern in self.process_patterns):
                                webapp_processes.append(proc)
                                self.logger.info(f"Processus trouvé: PID {proc_info['pid']} - {cmdline[:100]}")
                                continue
                    
                    # Vérification par ports utilisés - récupération séparée des connexions
                    try:
                        connections = proc.connections()
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr:
                                if conn.laddr.port in self.webapp_ports:
                                    webapp_processes.append(proc)
                                    self.logger.info(f"Processus sur port webapp: PID {proc_info['pid']} - Port {conn.laddr.port}")
                                    break
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        # Certains processus n'autorisent pas l'accès aux connexions
                        pass
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Processus disparu ou inaccessible
                    continue
                    
        except Exception as e:
            self.logger.error(f"Erreur énumération processus: {e}")
        
        # Suppression doublons
        unique_processes = []
        seen_pids = set()
        for proc in webapp_processes:
            if proc.pid not in seen_pids:
                unique_processes.append(proc)
                seen_pids.add(proc.pid)
        
        return unique_processes
    
    def _terminate_process_tree(self, proc: psutil.Process, timeout=3):
        """Termine un processus et tous ses enfants."""
        try:
            children = proc.children(recursive=True)
            all_procs = [proc] + children

            # Phase 1: SIGTERM
            for p in all_procs:
                try:
                    p.terminate()
                except psutil.NoSuchProcess:
                    continue
            
            gone, alive = psutil.wait_procs(all_procs, timeout=timeout)

            # Phase 2: SIGKILL pour les récalcitrants
            if alive:
                self.logger.warning(f"Processus récalcitrants détectés, envoi de SIGKILL: {[p.pid for p in alive]}")
                for p in alive:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        continue
                psutil.wait_procs(alive, timeout=timeout)

            self.logger.info(f"Arbre du processus PID {proc.pid} nettoyé.")

        except psutil.NoSuchProcess:
            self.logger.info(f"Processus PID {proc.pid} n'existait déjà plus.")
        except Exception as e:
            self.logger.error(f"Erreur lors de la terminaison de l'arbre du processus PID {proc.pid}: {e}")


    async def _terminate_processes_gracefully(self, processes: List[psutil.Process]):
        """Termine les processus de manière progressive en nettoyant leur arbre complet."""
        if not processes:
            return
        
        self.logger.info("Envoi signal TERM aux processus et à leurs enfants...")
        
        for proc in processes:
            self._terminate_process_tree(proc)

        # La vérification se fait maintenant dans _terminate_process_tree
        self.logger.info("Nettoyage par arbre de processus terminé.")
    
    async def _force_kill_remaining_processes(self):
        """Force l'arrêt des processus récalcitrants"""
        remaining_processes = self._find_webapp_processes()
        
        if not remaining_processes:
            return
        
        self.logger.warning(f"Force kill de {len(remaining_processes)} processus récalcitrants")
        
        for proc in remaining_processes:
            try:
                proc.kill()
                self.logger.warning(f"KILL forcé sur PID {proc.pid}")
                
                # Attente confirmation
                proc.wait(timeout=3)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
                self.logger.error(f"Impossible de tuer PID {proc.pid}: {e}")
    
    async def _check_port_liberation(self):
        """Vérifie la libération des ports de l'application"""
        self.logger.info("Vérification libération des ports...")
        
        occupied_ports = []
        for port in self.webapp_ports:
            if self._is_port_occupied(port):
                occupied_ports.append(port)
        
        if occupied_ports:
            self.logger.warning(f"Ports encore occupés: {occupied_ports}")
        else:
            self.logger.info("Tous les ports libérés")
    
    def _is_port_occupied(self, port: int) -> bool:
        """Vérifie si un port est occupé"""
        try:
            for conn in psutil.net_connections():
                if (hasattr(conn, 'laddr') and conn.laddr and 
                    conn.laddr.port == port and 
                    conn.status == psutil.CONN_LISTEN):
                    return True
        except (psutil.AccessDenied, AttributeError):
            pass
        return False
    
    async def _cleanup_temp_files(self):
        """Nettoie les fichiers temporaires de l'application"""
        self.logger.info("Nettoyage fichiers temporaires...")
        
        temp_files = [
            'backend_info.json',
            'test_integration_detailed.py',
            '.env.test',
            'test_detailed_output.log',
            'test_detailed_error.log',
            'integration_test_final.png'
        ]
        
        cleaned_count = 0
        for temp_file in temp_files:
            file_path = Path(temp_file)
            if file_path.exists():
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    self.logger.info(f"Supprimé: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Impossible de supprimer {temp_file}: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Fichiers temporaires nettoyés: {cleaned_count}")
        else:
            self.logger.info("Aucun fichier temporaire à nettoyer")
    
    def cleanup_by_pid(self, pids: List[int]):
        """Nettoie des processus spécifiques par PID"""
        self.logger.info(f"Nettoyage processus spécifiques: {pids}")
        
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                
                # Utilise la nouvelle méthode pour nettoyer l'arbre complet
                self._terminate_process_tree(proc)
                    
            except psutil.NoSuchProcess:
                self.logger.info(f"Processus PID {pid} déjà terminé")
            except psutil.AccessDenied:
                self.logger.error(f"Accès refusé pour PID {pid}")
            except Exception as e:
                self.logger.error(f"Erreur nettoyage PID {pid}: {e}")
    
    def cleanup_by_port(self, ports: List[int], max_attempts: int = 5, delay: float = 1.0):
        """Nettoie les processus utilisant des ports spécifiques de manière agressive."""
        self.logger.info(f"Nettoyage AGRESSIF des processus sur les ports: {ports} (max {max_attempts} tentatives)")

        for attempt in range(max_attempts):
            processes_to_kill = []
            occupied_ports = set()
            
            try:
                for conn in psutil.net_connections('tcp'):
                    if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port in ports:
                        occupied_ports.add(conn.laddr.port)
                        if conn.pid:
                            try:
                                proc = psutil.Process(conn.pid)
                                if proc not in processes_to_kill:
                                    processes_to_kill.append(proc)
                                    self.logger.info(f"[Tentative {attempt+1}] Processus trouvé sur port {conn.laddr.port}: PID {conn.pid} ({proc.name()})")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                self.logger.warning(f"Impossible d'accéder au processus avec PID {conn.pid} sur le port {conn.laddr.port}")
            except (psutil.AccessDenied, AttributeError) as e:
                self.logger.warning(f"Impossible d'énumérer les connexions réseau: {e}")

            if not processes_to_kill:
                if not occupied_ports:
                    self.logger.info("Succès. Tous les ports ciblés sont libres.")
                    return
                else:
                    self.logger.warning(f"Ports {list(occupied_ports)} sont occupés mais aucun processus correspondant n'a pu être identifié. Il s'agit peut-être de processus système.")

            # Nettoyage des processus trouvés
            if processes_to_kill:
                pids_to_kill = [p.pid for p in processes_to_kill]
                self.logger.info(f"Envoi du signal de terminaison aux PIDs: {pids_to_kill}")
                self.cleanup_by_pid(pids_to_kill)
            
            # Attendre avant la prochaine vérification
            self.logger.info(f"Attente de {delay}s avant la prochaine vérification...")
            time.sleep(delay)

        # Vérification finale
        final_occupied = [p for p in ports if self._is_port_occupied(p)]
        if final_occupied:
            self.logger.error(f"ÉCHEC du nettoyage : les ports {final_occupied} sont toujours occupés après {max_attempts} tentatives.")
        else:
            self.logger.success(f"Nettoyage par port réussi après {attempt + 1} tentative(s).")
    
    def get_webapp_processes_info(self) -> List[Dict[str, Any]]:
        """Retourne informations sur les processus webapp actifs"""
        processes = self._find_webapp_processes()
        
        processes_info = []
        for proc in processes:
            try:
                info = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'cmdline': ' '.join(proc.cmdline()),
                    'status': proc.status(),
                    'create_time': proc.create_time(),
                    'memory_info': proc.memory_info()._asdict(),
                    'connections': []
                }
                
                # Connections
                for conn in proc.connections():
                    if hasattr(conn, 'laddr') and conn.laddr:
                        info['connections'].append({
                            'port': conn.laddr.port,
                            'status': conn.status
                        })
                
                processes_info.append(info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes_info