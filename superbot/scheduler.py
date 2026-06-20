"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩
"""
import asyncio
import threading
import time
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import schedule
from concurrent.futures import ThreadPoolExecutor
import queue

log = logging.getLogger("scheduler")

class SuperBotScheduler:
    """
    Planificateur de tâches pour le SuperBot Trading Unifié.
    Gère l'exécution périodique de diverses tâches de maintenance et de monitoring.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialise le planificateur.

        Args:
            max_workers: Nombre maximum de workers pour l'exécution parallèle
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Scheduler")
        self.running = False
        self.scheduler_thread = None
        self.shutdown_event = threading.Event()
        self.job_queue = queue.Queue()
        self.jobs: Dict[str, Dict[str, Any]] = {}  # Nom du job -> configuration
        self.last_run_times: Dict[str, datetime] = {}  # Nom du job -> dernière exécution

        log.info(f"SuperBotScheduler initialisé avec {max_workers} workers")

    def start(self):
        """Démarre le planificateur en arrière-plan."""
        if self.running:
            log.warning("️  Le planificateur est déjà en cours d'exécution")
            return

        self.running = True
        self.shutdown_event.clear()
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        log.info("Planificateur démarré")

    def stop(self):
        """Arrête le planificateur de manière propre."""
        if not self.running:
            log.warning("️  Le planificateur n'est pas en cours d'exécution")
            return

        log.info("Arrêt du planificateur...")
        self.running = False
        self.shutdown_event.set()

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)

        # Arrêter l'executor
        self.executor.shutdown(wait=True)
        log.info("Planificateur arrêté")

    def schedule_job(self, name: str, func: Callable, interval_seconds: int,
                    run_immediately: bool = False, args: tuple = (), kwargs: dict = None):
        """
        Planifie une tâche récurrente.

        Args:
            name: Nom unique de la tâche
            func: Fonction à exécuter
            interval_seconds: Intervalle en secondes entre les exécutions
            run_immediately: Exécuter la tâche immédiatement au démarrage
            args: Arguments positionnels pour la fonction
            kwargs: Arguments nommés pour la fonction
        """
        if kwargs is None:
            kwargs = {}

        job_config = {
            'func': func,
            'interval_seconds': interval_seconds,
            'args': args,
            'kwargs': kwargs,
            'run_immediately': run_immediately,
            'last_run': None,
            'next_run': None,
            'run_count': 0,
            'error_count': 0,
            'last_error': None
        }

        self.jobs[name] = job_config
        self.last_run_times[name] = None

        # Planifier avec la bibliothèque schedule
        schedule.every(interval_seconds).seconds.do(
            self._add_job_to_queue, name
        ).tag(name)

        log.info(f"Tâche planifiée: '{name}' - Toutes les {interval_seconds}s")

        if run_immediately:
            self._add_job_to_queue(name)

    def schedule_daily(self, name: str, func: Callable, hour: int, minute: int = 0,
                      args: tuple = (), kwargs: dict = None):
        """
        Planifie une tâche quotidienne à une heure spécifique.

        Args:
            name: Nom unique de la tâche
            func: Fonction à exécuter
            hour: Heure d'exécution (0-23)
            minute: Minute d'exécution (0-59)
            args: Arguments positionnels pour la fonction
            kwargs: Arguments nommés pour la fonction
        """
        if kwargs is None:
            kwargs = {}

        job_config = {
            'func': func,
            'hour': hour,
            'minute': minute,
            'args': args,
            'kwargs': kwargs,
            'last_run': None,
            'next_run': None,
            'run_count': 0,
            'error_count': 0,
            'last_error': None,
            'type': 'daily'
        }

        self.jobs[name] = job_config
        self.last_run_times[name] = None

        # Planifier avec la bibliothèque schedule
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
            self._add_job_to_queue, name
        ).tag(name)

        log.info(f"Tâche quotidienne planifiée: '{name}' - Tous les jours à {hour:02d}:{minute:02d}")

    def schedule_weekly(self, name: str, func: Callable, day_of_week: int,
                       hour: int, minute: int = 0, args: tuple = (), kwargs: dict = None):
        """
        Planifie une tâche hebdomadaire.

        Args:
            name: Nom unique de la tâche
            func: Fonction à exécuter
            day_of_week: Jour de la semaine (0=lundi, 6=dimanche)
            hour: Heure d'exécution (0-23)
            minute: Minute d'exécution (0-59)
            args: Arguments positionnels pour la fonction
            kwargs: Arguments nommés pour la fonction
        """
        if kwargs is None:
            kwargs = {}

        # Mapping des jours: 0=monday, 1=tuesday, etc.
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_name = days[day_of_week]

        job_config = {
            'func': func,
            'day_of_week': day_of_week,
            'hour': hour,
            'minute': minute,
            'args': args,
            'kwargs': kwargs,
            'last_run': None,
            'next_run': None,
            'run_count': 0,
            'error_count': 0,
            'last_error': None,
            'type': 'weekly'
        }

        self.jobs[name] = job_config
        self.last_run_times[name] = None

        # Planifier avec la bibliothèque schedule
        getattr(schedule.every(), day_name).at(f"{hour:02d}:{minute:02d}").do(
            self._add_job_to_queue, name
        ).tag(name)

        log.info(f"Tâche hebdomadaire planifiée: '{name}' - Tous les {day_name} à {hour:02d}:{minute:02d}")

    def cancel_job(self, name: str):
        """
        Annule une tâche planifiée.

        Args:
            name: Nom de la tâche à annuler
        """
        if name in self.jobs:
            schedule.clear(name)
            del self.jobs[name]
            if name in self.last_run_times:
                del self.last_run_times[name]
            log.info(f"️  Tâche annulée: '{name}'")
        else:
            log.warning(f"️  Tâche '{name}' non trouvée pour annulation")

    def get_job_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retourne le statut d'une tâche planifiée.

        Args:
            name: Nom de la tâche

        Returns:
            Dictionnaire avec le statut de la tâche ou None si non trouvée
        """
        if name not in self.jobs:
            return None

        job = self.jobs[name]
        last_run = self.last_run_times.get(name)

        return {
            'name': name,
            'interval_seconds': job.get('interval_seconds'),
            'type': job.get('type', 'interval'),
            'run_count': job['run_count'],
            'error_count': job['error_count'],
            'last_error': job['last_error'],
            'last_run': last_run.isoformat() if last_run else None,
            'next_run': self._get_next_run_time(name),
            'is_scheduled': bool(self.jobs.get(name))
        }

    def get_all_jobs_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne le statut de toutes les tâches planifiées.

        Returns:
            Dictionnaire nom_de_tâche -> statut
        """
        return {name: self.get_job_status(name) for name in self.jobs.keys()}

    def _add_job_to_queue(self, name: str):
        """
        Ajoute une tâche à la file d'exécution (appelé par la bibliothèque schedule).

        Args:
            name: Nom de la tâche à exécuter
        """
        if name in self.jobs and not self.shutdown_event.is_set():
            try:
                self.job_queue.put_nowait(name)
            except queue.Full:
                log.warning(f"️  File d'attente pleine, tâche '{name}' ignorée")
        else:
            log.debug(f"Tâche '{name}' ignorée (planificateur arrêté ou tâche inexistante)")

    def _run_scheduler(self):
        """Boucle principale du planificateur."""
        log.debug("Boucle du planificateur démarrée")

        while self.running and not self.shutdown_event.is_set():
            try:
                # Exécuter les tâches pending de schedule
                schedule.run_pending()

                # Traiter la file d'attente des tâches à exécuter
                try:
                    # Timeout court pour permettre de vérifier régulièrement l'état d'arrêt
                    job_name = self.job_queue.get(timeout=1.0)
                    self._execute_job(job_name)
                except queue.Empty:
                    continue  # Aucune tâche à exécuter, continuer la boucle
                except Exception as e:
                    log.error(f"Erreur lors de la récupération d'une tâche de la file: {e}")

                # Dormir brièvement pour éviter l'utilisation excessive du CPU
                time.sleep(0.1)

            except Exception as e:
                log.error(f"Erreur dans la boucle du planificateur: {e}")
                time.sleep(1)  # Attendre un peu avant de reprendre

        log.debug("Boucle du planificateur terminée")

    def _execute_job(self, name: str):
        """
        Exécute une tâche spécifique.

        Args:
            name: Nom de la tâche à exécuter
        """
        if name not in self.jobs:
            log.warning(f"️  Tentative d'exécution d'une tâche inexistante: '{name}'")
            return

        job = self.jobs[name]
        start_time = datetime.now()

        try:
            log.debug(f"▶️  Exécution de la tâche: '{name}'")

            # Préparer les arguments
            args = job.get('args', ())
            kwargs = job.get('kwargs', {})

            # Exécuter la fonction dans le thread pool
            future = self.executor.submit(job['func'], *args, **kwargs)
            # Attendre le résultat avec timeout
            result = future.result(timeout=30.0)  # 30 secondes de timeout max

            # Mettre à jour les statistiques
            job['run_count'] += 1
            job['last_run'] = start_time
            self.last_run_times[name] = start_time

            # Réinitialiser le compteur d'erreurs en cas de succès consécutif
            if job['error_count'] > 0:
                log.info(f"Tâche '{name}' exécutée avec succès après {job['error_count']} erreur(s)")
                job['error_count'] = 0
                job['last_error'] = None
            else:
                log.debug(f"Tâche '{name}' exécutée avec succès")

        except Exception as e:
            # Gérer les erreurs d'exécution
            job['error_count'] += 1
            job['last_error'] = str(e)
            job['last_run'] = start_time
            self.last_run_times[name] = start_time

            log.error(f"Erreur lors de l'exécution de la tâche '{name}': {e}")
            log.debug(traceback.format_exc())

        finally:
            # Marquer la tâche comme terminée dans la file
            try:
                self.job_queue.task_done()
            except ValueError:
                pass  # Peut arriver si la tâche n'était pas dans la file

    def _get_next_run_time(self, name: str) -> Optional[str]:
        """
        Calcule la prochaine heure d'exécution estimée d'une tâche.

        Args:
            name: Nom de la tâche

        Returns:
            Chaîne ISO de la prochaine exécution ou None
        """
        if name not in self.jobs or name not in self.last_run_times:
            return None

        job = self.jobs[name]
        last_run = self.last_run_times[name]

        if job.get('type') == 'daily':
            # Prochaine exécution demain à la même heure
            next_run = last_run + timedelta(days=1)
            next_run = next_run.replace(hour=job['hour'], minute=job['minute'], second=0, microsecond=0)
        elif job.get('type') == 'weekly':
            # Prochaine exécution la semaine prochaine au même jour/heure
            days_ahead = 7 - last_run.weekday() + job['day_of_week']
            if days_ahead <= 0:  # Même jour ou déjà passé cette semaine
                days_ahead += 7
            next_run = last_run + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=job['hour'], minute=job['minute'], second=0, microsecond=0)
        else:
            # Tâche périodique standard
            interval_seconds = job.get('interval_seconds', 60)
            next_run = last_run + timedelta(seconds=interval_seconds)

        return next_run.isoformat()


# Instance globale du planificateur pour un accès facile
def setup_scheduler(max_workers: int = 4) -> SuperBotScheduler:
    """
    Configure et retourne une instance du planificateur.

    Args:
        max_workers: Nombre maximum de workers pour l'exécution parallèle

    Returns:
        Instance configurée de SuperBotScheduler
    """
    return SuperBotScheduler(max_workers=max_workers)


# Export des classes publiques
__all__ = ['SuperBotScheduler', 'setup_scheduler']