"""
Redis Failover System for Production-Grade Reliability

This module implements automatic failover across configured Redis instances
to handle monthly quota exhaustion gracefully. When one Redis instance hits quota limits,
the system automatically switches to the next available instance.

Features:
- Automatic failover on quota exhaustion
- Health monitoring and automatic recovery
- Transparent operation for existing code
- Production-grade error handling and logging
"""

import logging
import os
import threading
import time
import math
from dataclasses import dataclass
from typing import Any, Callable
from pathlib import Path

try:
    from dotenv import dotenv_values, load_dotenv
except Exception:
    def load_dotenv(*_args, **_kwargs):
        return False

    def dotenv_values(*_args, **_kwargs):
        return {}

from .runtime_infra import (
    install_socket_dns_fallback,
    managed_services_required,
)

try:
    import redis
    from redis import Redis
    from redis.exceptions import RedisError
except Exception:
    redis = None
    Redis = Any
    
    class RedisError(Exception):
        pass


logger = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ORIGINAL_ENV = dict(os.environ)
_ENV_LOADED = False


@dataclass(slots=True)
class RedisInstance:
    """Represents a single Redis instance configuration"""
    url: str
    name: str
    client: Redis | None = None
    error: str | None = None
    quota_exceeded: bool = False
    last_success: float = 0.0
    consecutive_failures: int = 0


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    used: int
    remaining: int
    retry_after_seconds: int


class DualRedisManager:
    """
    Manages configured Redis instances with automatic failover.
    
    When the preferred instance fails (especially due to quota exhaustion),
    automatically switches to the next configured instance. Periodically checks
    if the preferred instance has recovered and switches back.
    """
    
    def __init__(self):
        self._instances: list[RedisInstance] = []
        self._active_index = 0
        self._lock = threading.Lock()
        self._local_rate_limit_lock = threading.Lock()
        self._local_rate_limit_counters: dict[str, tuple[int, float]] = {}
        self._LOCAL_RATE_LIMIT_MAX_TRACKED = 50_000
        self._health_check_interval = 60.0  # Check every 60 seconds
        self._last_health_check = 0.0
        self._last_create_error: str | None = None
        
    def _load_environment_files(self) -> None:
        global _ENV_LOADED
        if _ENV_LOADED:
            return
        if self._running_under_pytest():
            return
        load_dotenv(_PROJECT_ROOT / ".env")
        local_values = dotenv_values(_PROJECT_ROOT / ".env.local")
        for key, value in local_values.items():
            if value is None:
                continue
            if key in _ORIGINAL_ENV:
                continue
            os.environ[key] = str(value)
        _ENV_LOADED = True
    
    def _running_under_pytest(self) -> bool:
        import sys
        if "PYTEST_CURRENT_TEST" in os.environ:
            return True
        if "pytest" in sys.modules:
            return True
        return any("pytest" in str(arg).lower() for arg in sys.argv)
    
    def _is_quota_exceeded_error(self, message: str | None) -> bool:
        raw = str(message or "").strip().lower()
        return "max requests limit exceeded" in raw or "quota" in raw
    
    def _socket_timeout_seconds(self) -> float:
        raw = (os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "1.5") or "").strip()
        try:
            value = float(raw)
        except ValueError:
            value = 1.5
        return max(0.2, min(10.0, value))
    
    def _socket_keepalive_enabled(self) -> bool:
        raw = (os.getenv("REDIS_SOCKET_KEEPALIVE", "true") or "").strip().lower()
        return raw in {"1", "true", "yes", "on"}
    
    def _retry_on_timeout_enabled(self) -> bool:
        raw = (os.getenv("REDIS_RETRY_ON_TIMEOUT", "true") or "").strip().lower()
        return raw in {"1", "true", "yes", "on"}
    
    def _redis_ssl_required(self) -> bool:
        raw = (os.getenv("REDIS_SSL_REQUIRED") or "").strip()
        if raw:
            return raw.lower() in {"1", "true", "yes", "on"}
        return managed_services_required()
    
    def _create_redis_client(self, url: str) -> Redis | None:
        """Create a Redis client for the given URL"""
        self._last_create_error = None
        if not url:
            self._last_create_error = "Redis URL is not configured"
            return None
        if redis is None:
            self._last_create_error = "redis package is not installed"
            return None
        
        try:
            install_socket_dns_fallback()
            client_kwargs: dict[str, Any] = {}
            
            # Parse URL to check for TLS
            from urllib.parse import urlparse
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            
            if scheme == "rediss":
                import ssl as ssl_module
                ssl_ca_file = (os.getenv("REDIS_SSL_CA_FILE") or "").strip()
                ssl_cert_file = (os.getenv("REDIS_SSL_CERT_FILE") or "").strip()
                ssl_key_file = (os.getenv("REDIS_SSL_KEY_FILE") or "").strip()
                ssl_cert_reqs_str = (os.getenv("REDIS_SSL_CERT_REQS") or "").strip().lower()
                ssl_check_hostname = (os.getenv("REDIS_SSL_CHECK_HOSTNAME", "true") or "").strip().lower() in {"1", "true", "yes", "on"}
                
                # Map string to ssl constant
                if ssl_cert_reqs_str == "none":
                    client_kwargs["ssl_cert_reqs"] = ssl_module.CERT_NONE
                elif ssl_cert_reqs_str == "optional":
                    client_kwargs["ssl_cert_reqs"] = ssl_module.CERT_OPTIONAL
                else:
                    client_kwargs["ssl_cert_reqs"] = ssl_module.CERT_REQUIRED
                
                client_kwargs["ssl_check_hostname"] = ssl_check_hostname
                
                if ssl_ca_file:
                    client_kwargs["ssl_ca_certs"] = ssl_ca_file
                if ssl_cert_file:
                    client_kwargs["ssl_certfile"] = ssl_cert_file
                if ssl_key_file:
                    client_kwargs["ssl_keyfile"] = ssl_key_file
            
            client: Redis = redis.Redis.from_url(
                url,
                decode_responses=True,
                socket_timeout=self._socket_timeout_seconds(),
                socket_connect_timeout=self._socket_timeout_seconds(),
                health_check_interval=30,
                socket_keepalive=self._socket_keepalive_enabled(),
                retry_on_timeout=self._retry_on_timeout_enabled(),
                **client_kwargs,
            )
            client.ping()
            probe_key = f"smartcampus:redis-probe:{os.getpid()}:{int(time.time())}"
            client.set(probe_key, "ok", ex=30)
            client.delete(probe_key)
            return client
        except Exception as exc:
            self._last_create_error = str(exc) or exc.__class__.__name__
            logger.warning("Failed to create Redis client for %s: %s", url[:30], exc)
            return None

    def _mark_instance_create_failed(self, instance: RedisInstance) -> None:
        """Preserve the connection failure reason for startup health status."""
        message = self._last_create_error or "Failed to connect"
        instance.error = message
        if self._is_quota_exceeded_error(message):
            instance.quota_exceeded = True

    def _configured_instances(self) -> list[RedisInstance]:
        configs = [
            ("primary", "REDIS_URL"),
            ("secondary", "REDIS_URL_SECONDARY"),
            ("tertiary", "REDIS_URL_TERTIARY"),
        ]
        instances: list[RedisInstance] = []
        for name, env_name in configs:
            url = (os.getenv(env_name) or "").strip()
            if url:
                instances.append(RedisInstance(url=url, name=name))
            elif name != "primary":
                logger.info("No %s Redis configured (%s not set)", name, env_name)
        return instances
    
    def initialize(self) -> bool:
        """Initialize configured Redis instances"""
        self._load_environment_files()

        configured_instances = self._configured_instances()
        if not any(instance.name == "primary" for instance in configured_instances):
            logger.error("REDIS_URL not configured")
            return False
        
        with self._lock:
            self._instances = []

            for instance in configured_instances:
                instance.client = self._create_redis_client(instance.url)
                if instance.client:
                    instance.last_success = time.time()
                    logger.info("%s Redis instance initialized successfully", instance.name.capitalize())
                else:
                    self._mark_instance_create_failed(instance)
                    logger.warning("%s Redis instance failed to initialize", instance.name.capitalize())
                self._instances.append(instance)
            
            # Set active instance to first working one
            self._active_index = 0
            for i, instance in enumerate(self._instances):
                if instance.client is not None:
                    self._active_index = i
                    logger.info("Active Redis instance: %s", instance.name)
                    break
            
            return any(inst.client is not None for inst in self._instances)
    
    def _mark_instance_failed(self, instance: RedisInstance, error: str) -> None:
        """Mark an instance as failed and check for quota exhaustion"""
        instance.consecutive_failures += 1
        instance.error = error
        
        if self._is_quota_exceeded_error(error):
            instance.quota_exceeded = True
            logger.warning(
                "Redis instance %s quota exceeded. Consecutive failures: %d",
                instance.name,
                instance.consecutive_failures
            )
        else:
            logger.warning(
                "Redis instance %s failed: %s. Consecutive failures: %d",
                instance.name,
                error,
                instance.consecutive_failures
            )
    
    def _mark_instance_success(self, instance: RedisInstance) -> None:
        """Mark an instance as successful"""
        instance.consecutive_failures = 0
        instance.error = None
        instance.quota_exceeded = False
        instance.last_success = time.time()
    
    def _try_failover(self) -> bool:
        """Attempt to failover to next available instance"""
        with self._lock:
            if len(self._instances) <= 1:
                return False
            
            current = self._instances[self._active_index]
            
            # Try each instance in order
            for i in range(len(self._instances)):
                next_index = (self._active_index + i + 1) % len(self._instances)
                next_instance = self._instances[next_index]
                
                # Skip if it's the current failing instance
                if next_index == self._active_index:
                    continue
                
                # Try to reconnect if client is None
                if next_instance.client is None:
                    next_instance.client = self._create_redis_client(next_instance.url)
                    if next_instance.client is None:
                        self._mark_instance_create_failed(next_instance)
                        continue
                
                # Test the instance
                if next_instance.client is not None:
                    try:
                        next_instance.client.ping()
                        self._active_index = next_index
                        self._mark_instance_success(next_instance)
                        logger.info(
                            "Failover successful: switched from %s to %s",
                            current.name,
                            next_instance.name
                        )
                        return True
                    except Exception as exc:
                        self._mark_instance_failed(next_instance, str(exc))
            
            logger.error("Failover failed: no healthy Redis instances available")
            return False
    
    def _periodic_health_check(self) -> None:
        """Periodically check if failed instances have recovered"""
        now = time.time()
        if now - self._last_health_check < self._health_check_interval:
            return
        
        self._last_health_check = now
        
        with self._lock:
            for i, instance in enumerate(self._instances):
                # Skip active instance
                if i == self._active_index:
                    continue
                
                # Try to recover failed instances
                if instance.client is None or instance.consecutive_failures > 0:
                    try:
                        if instance.client is None:
                            instance.client = self._create_redis_client(instance.url)
                            if instance.client is None:
                                self._mark_instance_create_failed(instance)
                                continue
                        
                        if instance.client:
                            instance.client.ping()
                            self._mark_instance_success(instance)
                            logger.info("Redis instance %s recovered", instance.name)
                            
                            # If this is primary and we're on a fallback, switch back
                            if i == 0 and self._active_index != 0:
                                self._active_index = 0
                                logger.info("Switched back to primary Redis instance")
                    except Exception as exc:
                        self._mark_instance_failed(instance, str(exc))
    
    def get_active_client(self) -> Redis | None:
        """Get the currently active Redis client"""
        self._periodic_health_check()
        
        with self._lock:
            if not self._instances:
                return None
            return self._instances[self._active_index].client
    
    def execute_with_failover(self, operation: Callable[[Redis], Any]) -> Any:
        """Execute an operation with automatic failover on failure"""
        max_attempts = len(self._instances) if self._instances else 1
        
        for attempt in range(max_attempts):
            client = self.get_active_client()
            if client is None:
                if attempt < max_attempts - 1:
                    self._try_failover()
                    continue
                raise RedisError("No Redis instances available")
            
            try:
                result = operation(client)
                with self._lock:
                    self._mark_instance_success(self._instances[self._active_index])
                return result
            except RedisError as exc:
                error_msg = str(exc)
                with self._lock:
                    self._mark_instance_failed(self._instances[self._active_index], error_msg)
                
                # Try failover if not last attempt
                if attempt < max_attempts - 1:
                    if self._try_failover():
                        continue
                
                raise
    
    def close_all(self) -> None:
        """Close all Redis connections"""
        with self._lock:
            for instance in self._instances:
                if instance.client:
                    try:
                        instance.client.close()
                    except Exception:
                        pass
                    instance.client = None
            self._instances = []
    
    def get_status(self) -> dict[str, Any]:
        """Get status of all Redis instances"""
        with self._lock:
            instances_status = []
            for i, instance in enumerate(self._instances):
                instances_status.append({
                    "name": instance.name,
                    "active": i == self._active_index,
                    "connected": instance.client is not None,
                    "quota_exceeded": instance.quota_exceeded,
                    "consecutive_failures": instance.consecutive_failures,
                    "error": instance.error,
                    "last_success": instance.last_success,
                })
            
            return {
                "dual_redis_enabled": len(self._instances) > 1,
                "active_instance": self._instances[self._active_index].name if self._instances else None,
                "instances": instances_status,
                "any_connected": any(inst.client is not None for inst in self._instances),
            }
    
    def _local_rate_limit_hit(self, redis_key: str, *, limit: int, window_seconds: int, now: float) -> RateLimitDecision:
        """Local in-memory rate limiting fallback"""
        expires_at_default = now + window_seconds
        with self._local_rate_limit_lock:
            if len(self._local_rate_limit_counters) > self._LOCAL_RATE_LIMIT_MAX_TRACKED:
                stale = [key for key, (_, expiry) in self._local_rate_limit_counters.items() if expiry <= now]
                for key in stale[:10_000]:
                    self._local_rate_limit_counters.pop(key, None)
            
            used, expires_at = self._local_rate_limit_counters.get(redis_key, (0, expires_at_default))
            if expires_at <= now:
                used = 0
                expires_at = expires_at_default
            used += 1
            self._local_rate_limit_counters[redis_key] = (used, expires_at)
        
        ttl = max(1, int(math.ceil(expires_at - now)))
        return RateLimitDecision(
            allowed=used <= limit,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            retry_after_seconds=ttl,
        )


# Global dual Redis manager instance
_dual_redis_manager = DualRedisManager()


def init_dual_redis(force: bool = False) -> bool:
    """Initialize the dual Redis system"""
    return _dual_redis_manager.initialize()


def get_dual_redis_client() -> Redis | None:
    """Get the active Redis client with failover support"""
    return _dual_redis_manager.get_active_client()


def execute_redis_with_failover(operation: Callable[[Redis], Any]) -> Any:
    """Execute a Redis operation with automatic failover"""
    return _dual_redis_manager.execute_with_failover(operation)


def close_dual_redis() -> None:
    """Close all Redis connections"""
    _dual_redis_manager.close_all()


def dual_redis_status() -> dict[str, Any]:
    """Get status of the dual Redis system"""
    return _dual_redis_manager.get_status()
