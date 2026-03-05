from __future__ import annotations

import importlib
import inspect
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote, urlparse, urlunparse

try:
    from redis import Redis as RedisClient
except Exception as exc:  # pragma: no cover - import surface depends on installed extras
    RedisClient = None
    REDIS_IMPORT_ERROR: Optional[Exception] = exc
else:
    REDIS_IMPORT_ERROR = None


TaskCallable = Callable[..., None]


def task_name_for_callable(fn: TaskCallable) -> str:
    module = str(getattr(fn, "__module__", "") or "__main__").strip() or "__main__"
    qualname = str(getattr(fn, "__qualname__", getattr(fn, "__name__", "task")) or "task")
    return f"{module}:{qualname}"


def callable_from_task_name(task_name: str) -> Optional[TaskCallable]:
    token = str(task_name or "").strip()
    if ":" not in token:
        return None
    module_name, qualname = token.split(":", 1)
    module_name = module_name.strip()
    qualname = qualname.strip()
    if not module_name or not qualname:
        return None
    try:
        target: Any = importlib.import_module(module_name)
    except Exception:
        return None
    for attr in qualname.split("."):
        if not attr or attr == "<locals>":
            return None
        if not hasattr(target, attr):
            return None
        target = getattr(target, attr)
    return target if callable(target) else None


def _mask_redis_url(url: str) -> str:
    parsed = urlparse(str(url or ""))
    if not parsed.scheme:
        return "redis://***"
    username = parsed.username
    password = parsed.password
    host = parsed.hostname or ""
    port = parsed.port
    netloc = ""
    if username:
        netloc += quote(username, safe="")
        netloc += ":***" if password is not None else ""
        netloc += "@"
    elif password is not None:
        netloc += ":***@"
    netloc += host
    if port is not None:
        netloc += f":{port}"
    path = parsed.path or "/0"
    return urlunparse((parsed.scheme, netloc, path, "", "", ""))


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_meta_scalar(value: Any, *, max_length: int = 200) -> Optional[str]:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return None
        return token[:max_length]
    return None


def _extract_task_metadata(fn: TaskCallable, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Optional[dict[str, str]]:
    metadata: dict[str, str] = {}

    # Prefer function signature-bound names when available.
    bound_args: Dict[str, Any] = {}
    try:
        signature = inspect.signature(fn)
        bound = signature.bind_partial(*args, **kwargs)
        bound_args = dict(bound.arguments)
    except Exception:
        bound_args = {}

    for key in ("job_id", "request_id", "start_at", "resume_from", "checkpoint_id", "donor_id", "tenant_id"):
        value = _coerce_meta_scalar(bound_args.get(key))
        if value:
            metadata[key] = value

    if "job_id" not in metadata:
        value = _coerce_meta_scalar(kwargs.get("job_id"))
        if value:
            metadata["job_id"] = value
        elif args and isinstance(args[0], str):
            first_arg = _coerce_meta_scalar(args[0], max_length=120)
            if first_arg:
                metadata["job_id"] = first_arg

    return metadata or None


@dataclass
class JobRunnerTask:
    fn: TaskCallable
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class InMemoryJobRunner:
    def __init__(self, worker_count: int = 2, queue_maxsize: int = 200) -> None:
        self.worker_count = max(1, int(worker_count))
        self.queue_maxsize = max(1, int(queue_maxsize))
        self._queue: queue.Queue[Optional[JobRunnerTask]] = queue.Queue(maxsize=self.queue_maxsize)
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._started = False
        self._submitted = 0
        self._completed = 0
        self._failed = 0

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._threads = []
            for idx in range(self.worker_count):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"grantflow-job-runner-{idx + 1}",
                    daemon=True,
                )
                worker.start()
                self._threads.append(worker)

    def stop(self, timeout_seconds: float = 2.0) -> None:
        with self._lock:
            if not self._started:
                return
            threads = list(self._threads)
            self._started = False
        for _ in threads:
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                # Worker threads will eventually drain real tasks and then consume sentinels.
                break
        for worker in threads:
            worker.join(timeout=max(0.0, float(timeout_seconds)))
        with self._lock:
            self._threads = []
            # Reset queue to drop stale sentinels/tasks between restarts.
            self._queue = queue.Queue(maxsize=self.queue_maxsize)

    def submit(self, fn: TaskCallable, *args: Any, **kwargs: Any) -> bool:
        if not callable(fn):
            raise TypeError("Job runner task must be callable")
        self.start()
        task = JobRunnerTask(fn=fn, args=tuple(args), kwargs=dict(kwargs))
        try:
            self._queue.put_nowait(task)
        except queue.Full:
            return False
        with self._lock:
            self._submitted += 1
        return True

    def is_running(self) -> bool:
        with self._lock:
            return self._started

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            submitted = int(self._submitted)
            completed = int(self._completed)
            failed = int(self._failed)
            running = bool(self._started)
            active_workers = sum(1 for t in self._threads if t.is_alive())
        return {
            "backend": "inmemory",
            "consumer_enabled": True,
            "running": running,
            "worker_count": self.worker_count,
            "active_workers": active_workers,
            "queue_maxsize": self.queue_maxsize,
            "queue_size": self._queue.qsize(),
            "submitted_count": submitted,
            "completed_count": completed,
            "failed_count": failed,
        }

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                self._queue.task_done()
                break
            try:
                task.fn(*task.args, **task.kwargs)
            except Exception:
                with self._lock:
                    self._failed += 1
            else:
                with self._lock:
                    self._completed += 1
            finally:
                self._queue.task_done()


class RedisJobRunner:
    def __init__(
        self,
        worker_count: int = 2,
        queue_maxsize: int = 200,
        *,
        redis_url: str = "redis://127.0.0.1:6379/0",
        queue_name: str = "grantflow:jobs",
        pop_timeout_seconds: float = 1.0,
        reconnect_sleep_seconds: float = 0.25,
        max_attempts: int = 3,
        dead_letter_queue_name: str = "",
        worker_heartbeat_key: str = "",
        worker_heartbeat_ttl_seconds: float = 45.0,
        allowed_import_prefixes: tuple[str, ...] = ("grantflow.",),
        redis_client_factory: Optional[Callable[[str], Any]] = None,
        consumer_enabled: bool = True,
    ) -> None:
        self.worker_count = max(1, int(worker_count))
        self.queue_maxsize = max(1, int(queue_maxsize))
        self.redis_url = str(redis_url or "redis://127.0.0.1:6379/0")
        self.queue_name = str(queue_name or "grantflow:jobs")
        self.max_attempts = max(1, _coerce_int(max_attempts, 3))
        dead_letter_token = str(dead_letter_queue_name or "").strip()
        self.dead_letter_queue_name = dead_letter_token if dead_letter_token else f"{self.queue_name}:dead"
        if self.dead_letter_queue_name == self.queue_name:
            self.dead_letter_queue_name = f"{self.queue_name}:dead"
        heartbeat_token = str(worker_heartbeat_key or "").strip()
        self.worker_heartbeat_key = heartbeat_token if heartbeat_token else f"{self.queue_name}:worker_heartbeat"
        self.worker_heartbeat_ttl_seconds = max(5.0, float(worker_heartbeat_ttl_seconds or 45.0))
        self.pop_timeout_seconds = max(0.1, float(pop_timeout_seconds))
        self.reconnect_sleep_seconds = max(0.05, float(reconnect_sleep_seconds))
        self.allowed_import_prefixes = tuple(
            str(p or "").strip() for p in allowed_import_prefixes if str(p or "").strip()
        )
        self._redis_client_factory = redis_client_factory
        self.consumer_enabled = bool(consumer_enabled)
        self._client: Any = None
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._started = False
        self._submitted = 0
        self._completed = 0
        self._failed = 0
        self._retried = 0
        self._requeued = 0
        self._dead_lettered = 0
        self._last_error: Optional[str] = None
        self._task_registry: dict[str, TaskCallable] = {}

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._threads = []
            if not self.consumer_enabled:
                return
            for idx in range(self.worker_count):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"grantflow-redis-job-runner-{idx + 1}",
                    daemon=True,
                )
                worker.start()
                self._threads.append(worker)

    def stop(self, timeout_seconds: float = 2.0) -> None:
        with self._lock:
            if not self._started:
                return
            threads = list(self._threads)
            self._started = False
        for worker in threads:
            worker.join(timeout=max(0.0, float(timeout_seconds)))
        with self._lock:
            self._threads = []

    def submit(self, fn: TaskCallable, *args: Any, **kwargs: Any) -> bool:
        if not callable(fn):
            raise TypeError("Job runner task must be callable")
        self.start()
        task_name = task_name_for_callable(fn)
        metadata = _extract_task_metadata(fn, tuple(args), dict(kwargs))
        payload: dict[str, Any] = {
            "dispatch_id": str(uuid.uuid4()),
            "task_name": task_name,
            "args": list(args),
            "kwargs": dict(kwargs),
            "attempt": 0,
            "max_attempts": self.max_attempts,
            "queued_at": time.time(),
        }
        if metadata:
            payload["metadata"] = metadata
        try:
            encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise TypeError("Redis job runner arguments must be JSON-serializable") from exc

        with self._lock:
            self._task_registry[task_name] = fn

        client = self._ensure_client()
        if client is None:
            return False
        try:
            current_size = int(client.llen(self.queue_name))
            if current_size >= self.queue_maxsize:
                return False
            client.rpush(self.queue_name, encoded)
        except Exception as exc:
            self._record_error(exc)
            return False
        with self._lock:
            self._submitted += 1
        return True

    def is_running(self) -> bool:
        with self._lock:
            return self._started

    def diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            submitted = int(self._submitted)
            completed = int(self._completed)
            failed = int(self._failed)
            retried = int(self._retried)
            requeued = int(self._requeued)
            dead_lettered = int(self._dead_lettered)
            running = bool(self._started)
            active_workers = sum(1 for t in self._threads if t.is_alive())
            last_error = self._last_error
        redis_available, availability_error = self._redis_available()
        queue_size = self._redis_queue_size(self.queue_name)
        dead_letter_queue_size = self._redis_queue_size(self.dead_letter_queue_name)
        if queue_size is None:
            queue_size = -1
        if dead_letter_queue_size is None:
            dead_letter_queue_size = -1
        if availability_error:
            last_error = availability_error
        worker_heartbeat = self.worker_heartbeat_status()
        return {
            "backend": "redis",
            "consumer_enabled": self.consumer_enabled,
            "running": running,
            "worker_count": self.worker_count,
            "active_workers": active_workers,
            "queue_maxsize": self.queue_maxsize,
            "queue_size": queue_size,
            "submitted_count": submitted,
            "completed_count": completed,
            "failed_count": failed,
            "retry_count": retried,
            "requeued_count": requeued,
            "dead_lettered_count": dead_lettered,
            "redis_url": _mask_redis_url(self.redis_url),
            "queue_name": self.queue_name,
            "max_attempts": self.max_attempts,
            "dead_letter_queue_name": self.dead_letter_queue_name,
            "dead_letter_queue_size": dead_letter_queue_size,
            "worker_heartbeat": worker_heartbeat,
            "redis_available": redis_available,
            "last_error": last_error,
        }

    def touch_worker_heartbeat(self, *, source: str = "worker") -> bool:
        client = self._ensure_client()
        if client is None:
            return False
        payload = {
            "ts": time.time(),
            "source": str(source or "worker").strip() or "worker",
            "pid": int(os.getpid()),
        }
        try:
            encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
            # TTL keeps key self-cleaning when worker disappears unexpectedly.
            ttl = max(10, int(round(self.worker_heartbeat_ttl_seconds * 2.0)))
            client.setex(self.worker_heartbeat_key, ttl, encoded)
            return True
        except Exception as exc:
            self._record_error(exc)
            return False

    def worker_heartbeat_status(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "key": self.worker_heartbeat_key,
            "ttl_seconds": float(self.worker_heartbeat_ttl_seconds),
            "present": False,
            "healthy": False,
        }
        client = self._ensure_client()
        if client is None:
            status["error"] = "redis_unavailable"
            return status
        try:
            raw = client.get(self.worker_heartbeat_key)
        except Exception as exc:
            self._record_error(exc)
            status["error"] = str(exc)
            return status
        if raw is None:
            return status

        if isinstance(raw, (bytes, bytearray)):
            decoded = raw.decode("utf-8", errors="replace")
        else:
            decoded = str(raw)
        ts_value: Any = None
        source = ""
        try:
            parsed = json.loads(decoded)
            if isinstance(parsed, dict):
                ts_value = parsed.get("ts")
                source = str(parsed.get("source") or "").strip()
            else:
                ts_value = parsed
        except Exception:
            ts_value = decoded

        try:
            last_seen = float(ts_value)
        except (TypeError, ValueError):
            status.update({"present": True, "parse_error": "invalid_timestamp"})
            return status

        age_seconds = max(0.0, time.time() - last_seen)
        status.update(
            {
                "present": True,
                "healthy": bool(age_seconds <= self.worker_heartbeat_ttl_seconds),
                "last_seen_unix": round(last_seen, 3),
                "age_seconds": round(age_seconds, 3),
            }
        )
        if source:
            status["source"] = source
        return status

    def _ensure_client(self) -> Any:
        with self._lock:
            client = self._client
        if client is not None:
            return client
        if REDIS_IMPORT_ERROR is not None and self._redis_client_factory is None:
            self._record_error(REDIS_IMPORT_ERROR)
            return None
        try:
            if self._redis_client_factory is not None:
                client = self._redis_client_factory(self.redis_url)
            else:
                assert RedisClient is not None
                client = RedisClient.from_url(self.redis_url, decode_responses=False)
        except Exception as exc:
            self._record_error(exc)
            return None
        with self._lock:
            self._client = client
        return client

    def _redis_available(self) -> tuple[bool, Optional[str]]:
        client = self._ensure_client()
        if client is None:
            with self._lock:
                return False, self._last_error
        try:
            ping = getattr(client, "ping", None)
            if callable(ping):
                ping()
            return True, None
        except Exception as exc:
            self._record_error(exc)
            return False, str(exc)

    def _redis_queue_size(self, queue_name: str) -> Optional[int]:
        client = self._ensure_client()
        if client is None:
            return None
        try:
            return int(client.llen(str(queue_name or self.queue_name)))
        except Exception as exc:
            self._record_error(exc)
            return None

    def _record_error(self, exc: Exception) -> None:
        with self._lock:
            self._last_error = str(exc)

    def _decode_queue_payload(self, raw_payload: Any) -> tuple[str, Optional[dict[str, Any]]]:
        if isinstance(raw_payload, (bytes, bytearray)):
            decoded_payload = raw_payload.decode("utf-8", errors="replace")
        else:
            decoded_payload = str(raw_payload)
        try:
            payload = json.loads(decoded_payload)
        except Exception:
            return decoded_payload, None
        return decoded_payload, payload if isinstance(payload, dict) else None

    def _is_task_payload(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        task_name = str(payload.get("task_name") or "").strip()
        return (
            bool(task_name)
            and isinstance(payload.get("args", []), list)
            and isinstance(payload.get("kwargs", {}), dict)
        )

    def list_dead_letters(self, limit: int = 50) -> Dict[str, Any]:
        client = self._ensure_client()
        if client is None:
            raise RuntimeError("Redis client is unavailable")
        limited = max(1, min(_coerce_int(limit, 50), 500))
        try:
            raw_items = client.lrange(self.dead_letter_queue_name, 0, limited - 1)
        except Exception as exc:
            self._record_error(exc)
            raise RuntimeError("Failed to read dead-letter queue") from exc

        items: list[dict[str, Any]] = []
        for idx, raw in enumerate(raw_items):
            decoded, parsed = self._decode_queue_payload(raw)
            if parsed is not None:
                item = dict(parsed)
            else:
                item = {"raw_payload": decoded, "reason": "unparseable_dead_letter_item"}
            if "task_name" not in item:
                embedded = item.get("payload")
                if isinstance(embedded, dict):
                    token = str(embedded.get("task_name") or "").strip()
                    if token:
                        item["task_name"] = token
                    if "dispatch_id" not in item:
                        dispatch_id = str(embedded.get("dispatch_id") or "").strip()
                        if dispatch_id:
                            item["dispatch_id"] = dispatch_id
                    if "metadata" not in item and isinstance(embedded.get("metadata"), dict):
                        item["metadata"] = dict(embedded.get("metadata") or {})
            if "job_id" not in item:
                metadata = item.get("metadata")
                if isinstance(metadata, dict):
                    job_id = str(metadata.get("job_id") or "").strip()
                    if job_id:
                        item["job_id"] = job_id
            item["index"] = idx
            items.append(item)

        size = self._redis_queue_size(self.dead_letter_queue_name)
        return {
            "mode": "redis_queue",
            "queue_name": self.queue_name,
            "dead_letter_queue_name": self.dead_letter_queue_name,
            "dead_letter_queue_size": int(size if size is not None else -1),
            "items": items,
        }

    def requeue_dead_letters(self, limit: int = 10, *, reset_attempts: bool = True) -> Dict[str, Any]:
        client = self._ensure_client()
        if client is None:
            raise RuntimeError("Redis client is unavailable")
        limited = max(1, min(_coerce_int(limit, 10), 500))
        existing_size = self._redis_queue_size(self.dead_letter_queue_name)
        if existing_size is None or existing_size <= 0:
            return {
                "mode": "redis_queue",
                "queue_name": self.queue_name,
                "dead_letter_queue_name": self.dead_letter_queue_name,
                "requested_count": limited,
                "affected_count": 0,
                "skipped_count": 0,
                "dead_letter_queue_size": max(0, int(existing_size or 0)),
            }

        to_scan = min(limited, max(0, int(existing_size)))
        moved = 0
        skipped = 0
        for _ in range(to_scan):
            try:
                raw_item = client.lpop(self.dead_letter_queue_name)
            except Exception as exc:
                self._record_error(exc)
                break
            if raw_item is None:
                break
            decoded, parsed = self._decode_queue_payload(raw_item)
            candidate: Optional[dict[str, Any]] = None
            if isinstance(parsed, dict):
                payload = parsed.get("payload")
                if self._is_task_payload(payload):
                    candidate = dict(payload)
                elif self._is_task_payload(parsed):
                    candidate = dict(parsed)
                if candidate is not None:
                    if "dispatch_id" not in candidate:
                        dispatch_id = str(parsed.get("dispatch_id") or "").strip()
                        if dispatch_id:
                            candidate["dispatch_id"] = dispatch_id
                    if "metadata" not in candidate and isinstance(parsed.get("metadata"), dict):
                        candidate["metadata"] = dict(parsed.get("metadata") or {})
            if candidate is None:
                skipped += 1
                try:
                    client.rpush(self.dead_letter_queue_name, decoded)
                except Exception as exc:
                    self._record_error(exc)
                continue

            if reset_attempts:
                candidate["attempt"] = 0
            candidate.pop("last_error", None)
            candidate.pop("last_error_at", None)
            if not isinstance(candidate.get("max_attempts"), int) or int(candidate.get("max_attempts") or 0) < 1:
                candidate["max_attempts"] = self.max_attempts

            try:
                encoded = json.dumps(candidate, ensure_ascii=True, separators=(",", ":"))
                client.rpush(self.queue_name, encoded)
                moved += 1
            except Exception as exc:
                self._record_error(exc)
                skipped += 1
                try:
                    client.rpush(self.dead_letter_queue_name, decoded)
                except Exception as nested_exc:
                    self._record_error(nested_exc)

        if moved:
            with self._lock:
                self._requeued += moved
        size = self._redis_queue_size(self.dead_letter_queue_name)
        return {
            "mode": "redis_queue",
            "queue_name": self.queue_name,
            "dead_letter_queue_name": self.dead_letter_queue_name,
            "requested_count": limited,
            "affected_count": moved,
            "skipped_count": skipped,
            "dead_letter_queue_size": int(size if size is not None else -1),
        }

    def purge_dead_letters(self, limit: int = 100) -> Dict[str, Any]:
        client = self._ensure_client()
        if client is None:
            raise RuntimeError("Redis client is unavailable")
        limited = max(1, min(_coerce_int(limit, 100), 5000))
        removed = 0
        for _ in range(limited):
            try:
                raw_item = client.lpop(self.dead_letter_queue_name)
            except Exception as exc:
                self._record_error(exc)
                break
            if raw_item is None:
                break
            removed += 1
        size = self._redis_queue_size(self.dead_letter_queue_name)
        return {
            "mode": "redis_queue",
            "queue_name": self.queue_name,
            "dead_letter_queue_name": self.dead_letter_queue_name,
            "requested_count": limited,
            "affected_count": removed,
            "dead_letter_queue_size": int(size if size is not None else -1),
        }

    def _resolve_task_callable(self, task_name: str) -> Optional[TaskCallable]:
        with self._lock:
            fn = self._task_registry.get(task_name)
        if callable(fn):
            return fn
        module_name = str(task_name.split(":", 1)[0] if ":" in task_name else "")
        if self.allowed_import_prefixes and not any(
            module_name.startswith(prefix) for prefix in self.allowed_import_prefixes
        ):
            return None
        resolved = callable_from_task_name(task_name)
        if callable(resolved):
            with self._lock:
                self._task_registry[task_name] = resolved
            return resolved
        return None

    def _retry_or_dead_letter(
        self,
        *,
        client: Any,
        payload: Optional[dict[str, Any]],
        raw_payload: str,
        task_name: str,
        reason: str,
        error: Optional[Exception] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        retry_payload = payload if isinstance(payload, dict) else None
        current_attempt = _coerce_int((retry_payload or {}).get("attempt"), 0)
        configured_max = _coerce_int((retry_payload or {}).get("max_attempts"), self.max_attempts)
        max_attempts = max(1, configured_max)
        next_attempt = current_attempt + 1
        dispatch_id = str((retry_payload or {}).get("dispatch_id") or "").strip()
        queued_at = (retry_payload or {}).get("queued_at")
        first_failed_at = (retry_payload or {}).get("first_failed_at")
        if first_failed_at is None:
            first_failed_at = time.time()
        payload_metadata = (
            dict((retry_payload or {}).get("metadata") or {})
            if isinstance((retry_payload or {}).get("metadata"), dict)
            else {}
        )
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                token = _coerce_meta_scalar(value)
                if token:
                    payload_metadata[str(key)] = token
        non_retry_reasons = {
            "invalid_payload_json",
            "invalid_payload_shape",
            "invalid_task_envelope",
            "task_not_resolved",
        }
        retry_allowed = reason not in non_retry_reasons

        if retry_payload is not None and retry_allowed and next_attempt < max_attempts:
            retried_payload = dict(retry_payload)
            retried_payload["attempt"] = next_attempt
            retried_payload["max_attempts"] = max_attempts
            if dispatch_id:
                retried_payload["dispatch_id"] = dispatch_id
            if queued_at is not None:
                retried_payload["queued_at"] = queued_at
            retried_payload["first_failed_at"] = first_failed_at
            if payload_metadata:
                retried_payload["metadata"] = payload_metadata
            if error is not None:
                retried_payload["last_error"] = str(error)
                retried_payload["last_error_at"] = time.time()
            try:
                encoded = json.dumps(retried_payload, ensure_ascii=True, separators=(",", ":"))
                client.rpush(self.queue_name, encoded)
                with self._lock:
                    self._retried += 1
                return
            except Exception as exc:
                self._record_error(exc)
                reason = f"retry_enqueue_failed:{reason}"

        dead_letter_payload: dict[str, Any] = {
            "source_queue": self.queue_name,
            "task_name": task_name or str((retry_payload or {}).get("task_name") or "").strip(),
            "reason": reason,
            "attempt": next_attempt,
            "max_attempts": max_attempts,
            "failed_at": time.time(),
        }
        if dispatch_id:
            dead_letter_payload["dispatch_id"] = dispatch_id
        if queued_at is not None:
            dead_letter_payload["queued_at"] = queued_at
        if first_failed_at is not None:
            dead_letter_payload["first_failed_at"] = first_failed_at
        if payload_metadata:
            dead_letter_payload["metadata"] = payload_metadata
            job_id = str(payload_metadata.get("job_id") or "").strip()
            if job_id:
                dead_letter_payload["job_id"] = job_id
        if retry_payload is not None:
            dead_letter_payload["payload"] = retry_payload
        else:
            dead_letter_payload["raw_payload"] = raw_payload
        if error is not None:
            dead_letter_payload["error"] = str(error)

        try:
            encoded_dead_letter = json.dumps(dead_letter_payload, ensure_ascii=True, separators=(",", ":"))
            client.rpush(self.dead_letter_queue_name, encoded_dead_letter)
            with self._lock:
                self._dead_lettered += 1
        except Exception as exc:
            self._record_error(exc)

        with self._lock:
            self._failed += 1

    def _worker_loop(self) -> None:
        while True:
            with self._lock:
                if not self._started:
                    break
            client = self._ensure_client()
            if client is None:
                time.sleep(self.reconnect_sleep_seconds)
                continue
            try:
                item = client.blpop(self.queue_name, timeout=max(1, int(round(self.pop_timeout_seconds))))
            except Exception as exc:
                self._record_error(exc)
                time.sleep(self.reconnect_sleep_seconds)
                continue
            if not item:
                continue
            raw_payload: Any = item
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                raw_payload = item[1]
            if isinstance(raw_payload, (bytes, bytearray)):
                decoded_payload = raw_payload.decode("utf-8", errors="replace")
            else:
                decoded_payload = str(raw_payload)
            try:
                payload = json.loads(decoded_payload)
            except Exception as exc:
                self._retry_or_dead_letter(
                    client=client,
                    payload=None,
                    raw_payload=decoded_payload,
                    task_name="",
                    reason="invalid_payload_json",
                    error=exc,
                    metadata=None,
                )
                continue
            if not isinstance(payload, dict):
                self._retry_or_dead_letter(
                    client=client,
                    payload=None,
                    raw_payload=decoded_payload,
                    task_name="",
                    reason="invalid_payload_shape",
                    error=None,
                    metadata=None,
                )
                continue
            task_name = str(payload.get("task_name") or "").strip()
            args = payload.get("args", [])
            kwargs = payload.get("kwargs", {})
            payload_metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None
            if not task_name or not isinstance(args, list) or not isinstance(kwargs, dict):
                self._retry_or_dead_letter(
                    client=client,
                    payload=payload,
                    raw_payload=decoded_payload,
                    task_name=task_name,
                    reason="invalid_task_envelope",
                    error=None,
                    metadata=payload_metadata,
                )
                continue
            fn = self._resolve_task_callable(task_name)
            if fn is None:
                self._retry_or_dead_letter(
                    client=client,
                    payload=payload,
                    raw_payload=decoded_payload,
                    task_name=task_name,
                    reason="task_not_resolved",
                    error=None,
                    metadata=payload_metadata,
                )
                continue
            try:
                fn(*tuple(args), **kwargs)
            except Exception as exc:
                self._retry_or_dead_letter(
                    client=client,
                    payload=payload,
                    raw_payload=decoded_payload,
                    task_name=task_name,
                    reason="task_execution_error",
                    error=exc,
                    metadata=payload_metadata,
                )
            else:
                with self._lock:
                    self._completed += 1
