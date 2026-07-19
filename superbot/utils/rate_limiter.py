"""
Utilitaires de limitation du débit d'appels API.
Fournit un décorateur `with_exponential_backoff` pour retenter automatiquement
les appels API qui échouent avec une erreur de rate-limit (429) ou serveur (5xx).
"""
import time
import random
import logging
import functools

log = logging.getLogger("rate_limiter")


def with_exponential_backoff(max_retries: int = 5, base_delay: float = 1.0,
                              max_delay: float = 60.0, jitter: bool = True):
    """
    Décorateur qui retente une fonction en cas d'exception avec un délai exponentiel.

    Args:
        max_retries: Nombre maximum de tentatives (défaut: 5).
        base_delay:  Délai de base en secondes avant la première relance (défaut: 1s).
        max_delay:   Délai maximum en secondes entre deux tentatives (défaut: 60s).
        jitter:      Ajoute un bruit aléatoire ±20% pour éviter les tempêtes de reconnexion.

    Usage:
        @with_exponential_backoff(max_retries=3, base_delay=1.0)
        def ma_fonction():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()

                    # Détecter si l'erreur est retriable (rate-limit ou erreur serveur)
                    is_rate_limit = (
                        "429" in error_str or
                        "too many requests" in error_str or
                        "rate limit" in error_str or
                        "exceeded" in error_str
                    )
                    is_server_error = (
                        "500" in error_str or "502" in error_str or
                        "503" in error_str or "504" in error_str or
                        "timeout" in error_str or "connection" in error_str
                    )

                    if attempt >= max_retries:
                        log.error(
                            f"[RateLimiter] Échec définitif après {max_retries + 1} tentatives : {e}"
                        )
                        raise last_exception

                    if is_rate_limit or is_server_error:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        if jitter:
                            # Jitter ±20% pour éviter les tempêtes de reconnexion
                            delay *= (0.8 + random.random() * 0.4)
                        log.warning(
                            f"[RateLimiter] Erreur API (tentative {attempt + 1}/{max_retries + 1}) : {e}. "
                            f"Nouvelle tentative dans {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        # Erreur non-retriable → propager immédiatement
                        raise e

            raise last_exception
        return wrapper
    return decorator


__all__ = ["with_exponential_backoff"]
