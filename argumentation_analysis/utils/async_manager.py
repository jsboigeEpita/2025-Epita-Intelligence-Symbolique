#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestionnaire asynchrone hybride pour l'analyse argumentative.

Ce module fournit une interface unifiée pour gérer les appels synchrones et
asynchrones avec gestion robuste des timeouts et des erreurs.
"""

import asyncio
import logging
import functools
import threading
import time
from typing import Any, Callable, Coroutine, Optional, Union, Dict, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ConcurrentTimeoutError
from datetime import datetime, timedelta


class AsyncManager:
    """
    Gestionnaire asynchrone hybride avec gestion des timeouts et fallbacks.
    
    Cette classe permet d'exécuter des fonctions synchrones et asynchrones
    de manière unifiée avec une gestion robuste des erreurs.
    """
    
    def __init__(self, max_workers: int = 4, default_timeout: float = 30.0):
        """
        Initialise le gestionnaire asynchrone.
        
        Args:
            max_workers: Nombre maximum de workers pour le ThreadPoolExecutor
            default_timeout: Timeout par défaut en secondes
        """
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.task_counter = 0
        self._loop = None
        
    def get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """
        Obtient ou crée une boucle d'événements.
        
        Returns:
            Boucle d'événements asyncio
        """
        try:
            # Essayer d'obtenir la boucle actuelle
            return asyncio.get_running_loop()
        except RuntimeError:
            # Aucune boucle en cours, en créer une nouvelle
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop
    
    def run_hybrid(
        self, 
        func_or_coro: Union[Callable, Coroutine], 
        *args, 
        timeout: Optional[float] = None,
        fallback_result: Any = None,
        **kwargs
    ) -> Any:
        """
        Exécute une fonction/coroutine de manière hybride sync/async.
        
        Args:
            func_or_coro: Fonction ou coroutine à exécuter
            *args: Arguments positionnels
            timeout: Timeout en secondes (utilise default_timeout si None)
            fallback_result: Résultat à retourner en cas d'échec
            **kwargs: Arguments nommés
            
        Returns:
            Résultat de l'exécution ou fallback_result
        """
        task_id = self._generate_task_id()
        timeout = timeout or self.default_timeout
        
        self.logger.debug(f"Exécution hybride task_{task_id}: {func_or_coro}")
        
        try:
            self.active_tasks[task_id] = {
                'start_time': datetime.now(),
                'timeout': timeout,
                'status': 'running'
            }
            
            # Déterminer le type et exécuter
            if asyncio.iscoroutine(func_or_coro):
                result = self._run_coroutine(func_or_coro, timeout)
            elif asyncio.iscoroutinefunction(func_or_coro):
                coro = func_or_coro(*args, **kwargs)
                result = self._run_coroutine(coro, timeout)
            else:
                result = self._run_sync_function(func_or_coro, args, kwargs, timeout)
            
            self.active_tasks[task_id]['status'] = 'completed'
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution task_{task_id}: {e}")
            self.active_tasks[task_id]['status'] = 'error'
            self.active_tasks[task_id]['error'] = str(e)
            return fallback_result
            
        finally:
            # Nettoyage
            if task_id in self.active_tasks:
                end_time = datetime.now()
                self.active_tasks[task_id]['end_time'] = end_time
                self.active_tasks[task_id]['duration'] = (
                    end_time - self.active_tasks[task_id]['start_time']
                ).total_seconds()
    
    def _run_coroutine(self, coro: Coroutine, timeout: float) -> Any:
        """
        Exécute une coroutine avec timeout.
        
        Args:
            coro: Coroutine à exécuter
            timeout: Timeout en secondes
            
        Returns:
            Résultat de la coroutine
        """
        try:
            loop = self.get_or_create_event_loop()
            
            if loop.is_running():
                # Si la boucle est déjà en cours, créer une tâche
                future = asyncio.create_task(coro)
                return asyncio.wait_for(future, timeout=timeout)
            else:
                # Exécuter la coroutine dans la boucle
                return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
                
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout lors de l'exécution de la coroutine après {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la coroutine: {e}")
            raise
    
    def _run_sync_function(
        self, 
        func: Callable, 
        args: tuple, 
        kwargs: dict, 
        timeout: float
    ) -> Any:
        """
        Exécute une fonction synchrone avec timeout.
        
        Args:
            func: Fonction à exécuter
            args: Arguments positionnels
            kwargs: Arguments nommés
            timeout: Timeout en secondes
            
        Returns:
            Résultat de la fonction
        """
        try:
            future = self.executor.submit(func, *args, **kwargs)
            return future.result(timeout=timeout)
            
        except ConcurrentTimeoutError:
            self.logger.warning(f"Timeout lors de l'exécution de la fonction après {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la fonction: {e}")
            raise
    
    def run_multiple_hybrid(
        self, 
        tasks: List[Dict[str, Any]], 
        max_concurrent: int = 5,
        global_timeout: float = 60.0
    ) -> List[Any]:
        """
        Exécute plusieurs tâches en parallèle de manière hybride.
        
        Args:
            tasks: Liste de dictionnaires avec 'func', 'args', 'kwargs'
            max_concurrent: Nombre maximum de tâches concurrentes
            global_timeout: Timeout global en secondes
            
        Returns:
            Liste des résultats
        """
        self.logger.info(f"Exécution de {len(tasks)} tâches en parallèle")
        
        results = []
        start_time = time.time()
        
        # Diviser les tâches en batches
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = []
            
            # Vérifier le timeout global
            elapsed = time.time() - start_time
            if elapsed >= global_timeout:
                self.logger.warning("Timeout global atteint")
                break
            
            remaining_timeout = global_timeout - elapsed
            
            for task_def in batch:
                try:
                    func = task_def['func']
                    args = task_def.get('args', ())
                    kwargs = task_def.get('kwargs', {})
                    task_timeout = task_def.get('timeout', min(remaining_timeout / len(batch), 10.0))
                    fallback = task_def.get('fallback_result')
                    
                    result = self.run_hybrid(func, *args, timeout=task_timeout, fallback_result=fallback, **kwargs)
                    batch_results.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Erreur dans une tâche du batch: {e}")
                    batch_results.append(task_def.get('fallback_result'))
            
            results.extend(batch_results)
        
        return results
    
    def create_async_wrapper(self, sync_func: Callable) -> Callable:
        """
        Crée un wrapper asynchrone pour une fonction synchrone.
        
        Args:
            sync_func: Fonction synchrone à wrapper
            
        Returns:
            Fonction asynchrone wrapper
        """
        @functools.wraps(sync_func)
        async def async_wrapper(*args, **kwargs):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.executor, sync_func, *args, **kwargs)
        
        return async_wrapper
    
    def create_sync_wrapper(self, async_func: Callable) -> Callable:
        """
        Crée un wrapper synchrone pour une fonction asynchrone.
        
        Args:
            async_func: Fonction asynchrone à wrapper
            
        Returns:
            Fonction synchrone wrapper
        """
        @functools.wraps(async_func)
        def sync_wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(async_func):
                coro = async_func(*args, **kwargs)
            else:
                coro = async_func
            
            return self.run_hybrid(coro)
        
        return sync_wrapper
    
    def _generate_task_id(self) -> str:
        """Génère un ID unique pour une tâche."""
        self.task_counter += 1
        return f"task_{self.task_counter}_{int(time.time())}"
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """
        Retourne les tâches actives.
        
        Returns:
            Dictionnaire des tâches actives
        """
        return self.active_tasks.copy()
    
    def cleanup_completed_tasks(self, max_age_hours: int = 1) -> int:
        """
        Nettoie les tâches terminées anciennes.
        
        Args:
            max_age_hours: Âge maximum en heures
            
        Returns:
            Nombre de tâches nettoyées
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_remove = []
        
        for task_id, task_info in self.active_tasks.items():
            if (task_info.get('status') in ['completed', 'error'] and 
                task_info.get('end_time', datetime.now()) < cutoff):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]
        
        self.logger.debug(f"Nettoyé {len(to_remove)} tâches anciennes")
        return len(to_remove)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de performance.
        
        Returns:
            Dictionnaire des statistiques
        """
        completed_tasks = [
            task for task in self.active_tasks.values() 
            if task.get('status') == 'completed' and 'duration' in task
        ]
        
        if not completed_tasks:
            return {
                'total_tasks': len(self.active_tasks),
                'completed_tasks': 0,
                'error_tasks': len([t for t in self.active_tasks.values() if t.get('status') == 'error']),
                'average_duration': 0,
                'max_duration': 0,
                'min_duration': 0
            }
        
        durations = [task['duration'] for task in completed_tasks]
        
        return {
            'total_tasks': len(self.active_tasks),
            'completed_tasks': len(completed_tasks),
            'error_tasks': len([t for t in self.active_tasks.values() if t.get('status') == 'error']),
            'average_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'min_duration': min(durations)
        }
    
    def shutdown(self):
        """Arrête proprement le gestionnaire asynchrone."""
        self.logger.info("Arrêt du gestionnaire asynchrone...")
        
        try:
            self.executor.shutdown(wait=True)
            
            if self._loop and not self._loop.is_closed():
                # Annuler toutes les tâches en cours
                pending_tasks = [task for task in asyncio.all_tasks(self._loop) if not task.done()]
                for task in pending_tasks:
                    task.cancel()
                
                # Fermer la boucle
                self._loop.close()
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt: {e}")


# Instance globale
async_manager = AsyncManager()


def run_hybrid_safe(
    func_or_coro: Union[Callable, Coroutine], 
    *args, 
    timeout: Optional[float] = None,
    fallback_result: Any = None,
    **kwargs
) -> Any:
    """
    Fonction utilitaire pour exécuter de manière hybride et sûre.
    
    Args:
        func_or_coro: Fonction ou coroutine à exécuter
        *args: Arguments positionnels
        timeout: Timeout en secondes
        fallback_result: Résultat de fallback
        **kwargs: Arguments nommés
        
    Returns:
        Résultat de l'exécution
    """
    return async_manager.run_hybrid(func_or_coro, *args, timeout=timeout, fallback_result=fallback_result, **kwargs)


def ensure_async(func: Callable) -> Callable:
    """
    Décorateur pour s'assurer qu'une fonction est asynchrone.
    
    Args:
        func: Fonction à rendre asynchrone si nécessaire
        
    Returns:
        Fonction asynchrone
    """
    if asyncio.iscoroutinefunction(func):
        return func
    else:
        return async_manager.create_async_wrapper(func)


def ensure_sync(func: Callable) -> Callable:
    """
    Décorateur pour s'assurer qu'une fonction est synchrone.
    
    Args:
        func: Fonction à rendre synchrone si nécessaire
        
    Returns:
        Fonction synchrone
    """
    if asyncio.iscoroutinefunction(func):
        return async_manager.create_sync_wrapper(func)
    else:
        return func