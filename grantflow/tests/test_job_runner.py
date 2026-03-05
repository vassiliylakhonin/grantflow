import json
import threading
import time

from grantflow.core.job_runner import InMemoryJobRunner, RedisJobRunner


_REDIS_TEST_OBSERVED: list[int] = []
_REDIS_OBSERVED_LOCK = threading.Lock()


def _redis_test_task(value: int) -> None:
    with _REDIS_OBSERVED_LOCK:
        _REDIS_TEST_OBSERVED.append(int(value))


class _FakeRedisClient:
    def __init__(self) -> None:
        self._queues: dict[str, list[bytes]] = {}
        self._kv: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def ping(self) -> bool:
        return True

    def llen(self, queue_name: str) -> int:
        with self._lock:
            return len(self._queues.get(queue_name, []))

    def rpush(self, queue_name: str, payload: str) -> int:
        with self._lock:
            queue = self._queues.setdefault(queue_name, [])
            queue.append(payload.encode("utf-8"))
            return len(queue)

    def setex(self, key: str, ttl_seconds: int, payload: str) -> bool:
        _ = int(ttl_seconds)
        with self._lock:
            self._kv[str(key)] = payload.encode("utf-8")
        return True

    def get(self, key: str):
        with self._lock:
            return self._kv.get(str(key))

    def blpop(self, queue_name: str, timeout: int = 1):
        deadline = time.time() + max(0, int(timeout))
        while True:
            with self._lock:
                queue = self._queues.setdefault(queue_name, [])
                if queue:
                    payload = queue.pop(0)
                    return (queue_name.encode("utf-8"), payload)
            if time.time() >= deadline:
                return None
            time.sleep(0.01)

    def lrange(self, queue_name: str, start: int, end: int):
        with self._lock:
            queue = list(self._queues.get(queue_name, []))
        safe_start = max(0, int(start))
        safe_end = int(end)
        if safe_end < 0:
            safe_end = len(queue) + safe_end
        safe_end = min(safe_end, len(queue) - 1)
        if safe_start > safe_end or safe_start >= len(queue):
            return []
        return queue[safe_start : safe_end + 1]

    def lpop(self, queue_name: str):
        with self._lock:
            queue = self._queues.setdefault(queue_name, [])
            if not queue:
                return None
            return queue.pop(0)

    def queue_snapshot(self, queue_name: str) -> list[str]:
        with self._lock:
            raw = list(self._queues.get(queue_name, []))
        return [item.decode("utf-8", errors="replace") for item in raw]


class _AlwaysFullRedisClient(_FakeRedisClient):
    def llen(self, queue_name: str) -> int:
        _ = queue_name
        return 999999


def _wait_until(predicate, timeout_s: float = 1.5) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_inmemory_job_runner_executes_tasks():
    runner = InMemoryJobRunner(worker_count=1, queue_maxsize=8)
    observed: list[int] = []

    def _task(value: int) -> None:
        observed.append(value)

    assert runner.submit(_task, 1) is True
    assert _wait_until(lambda: observed == [1])
    diag = runner.diagnostics()
    assert diag["completed_count"] >= 1
    assert diag["failed_count"] == 0
    runner.stop()


def test_inmemory_job_runner_counts_failures_and_keeps_running():
    runner = InMemoryJobRunner(worker_count=1, queue_maxsize=8)
    observed = {"ok": 0}

    def _bad_task() -> None:
        raise RuntimeError("boom")

    def _good_task() -> None:
        observed["ok"] += 1

    assert runner.submit(_bad_task) is True
    assert runner.submit(_good_task) is True
    assert _wait_until(lambda: observed["ok"] == 1)
    diag = runner.diagnostics()
    assert diag["failed_count"] >= 1
    assert diag["completed_count"] >= 1
    runner.stop()


def test_inmemory_job_runner_rejects_submit_when_queue_is_full():
    runner = InMemoryJobRunner(worker_count=1, queue_maxsize=1)
    blocker = threading.Event()
    started = threading.Event()

    def _blocking_task() -> None:
        started.set()
        blocker.wait(timeout=0.5)

    assert runner.submit(_blocking_task) is True
    assert started.wait(timeout=0.5)
    assert runner.submit(_blocking_task) is True
    assert runner.submit(_blocking_task) is False
    blocker.set()
    assert _wait_until(lambda: runner.diagnostics()["completed_count"] >= 2)
    runner.stop()


def test_redis_job_runner_executes_tasks_with_fake_client():
    fake_client = _FakeRedisClient()
    with _REDIS_OBSERVED_LOCK:
        _REDIS_TEST_OBSERVED.clear()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs",
        pop_timeout_seconds=0.1,
        redis_client_factory=lambda _url: fake_client,
    )

    assert runner.submit(_redis_test_task, 7) is True
    assert _wait_until(lambda: _REDIS_TEST_OBSERVED == [7])
    diag = runner.diagnostics()
    assert diag["backend"] == "redis"
    assert diag["redis_available"] is True
    assert diag["completed_count"] >= 1
    assert diag["failed_count"] == 0
    assert diag["retry_count"] == 0
    assert diag["dead_lettered_count"] == 0
    assert isinstance(diag.get("worker_heartbeat"), dict)
    runner.stop()


def test_redis_job_runner_rejects_non_json_serializable_args():
    fake_client = _FakeRedisClient()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:opaque",
        pop_timeout_seconds=0.1,
        redis_client_factory=lambda _url: fake_client,
    )
    try:
        try:
            runner.submit(_redis_test_task, object())
            assert False, "Expected submit to reject non-JSON arguments"
        except TypeError as exc:
            assert "JSON-serializable" in str(exc)
    finally:
        runner.stop()


def test_redis_job_runner_rejects_submit_when_queue_is_full():
    fake_client = _AlwaysFullRedisClient()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=1,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:full",
        pop_timeout_seconds=1.0,
        redis_client_factory=lambda _url: fake_client,
    )
    assert runner.submit(_redis_test_task, 1) is False
    runner.stop()


def test_redis_job_runner_retries_then_succeeds():
    fake_client = _FakeRedisClient()
    seen = {"calls": 0}

    def _flaky(value: int) -> None:
        seen["calls"] += 1
        if seen["calls"] == 1:
            raise RuntimeError("transient")
        _redis_test_task(value)

    with _REDIS_OBSERVED_LOCK:
        _REDIS_TEST_OBSERVED.clear()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:retry-success",
        pop_timeout_seconds=0.1,
        max_attempts=3,
        redis_client_factory=lambda _url: fake_client,
    )
    try:
        assert runner.submit(_flaky, 9) is True
        assert _wait_until(lambda: _REDIS_TEST_OBSERVED == [9], timeout_s=2.0)
        diag = runner.diagnostics()
        assert diag["completed_count"] >= 1
        assert diag["failed_count"] == 0
        assert diag["retry_count"] >= 1
        assert diag["dead_lettered_count"] == 0
        assert fake_client.queue_snapshot(diag["dead_letter_queue_name"]) == []
    finally:
        runner.stop()


def test_redis_job_runner_dead_letters_after_max_attempts():
    fake_client = _FakeRedisClient()

    def _always_fail(_value: int) -> None:
        raise RuntimeError("always bad")

    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:retry-fail",
        pop_timeout_seconds=0.1,
        max_attempts=2,
        redis_client_factory=lambda _url: fake_client,
    )
    try:
        assert runner.submit(_always_fail, 5) is True
        assert _wait_until(lambda: runner.diagnostics()["dead_lettered_count"] >= 1, timeout_s=2.0)
        diag = runner.diagnostics()
        assert diag["failed_count"] >= 1
        assert diag["retry_count"] >= 1
        assert diag["dead_lettered_count"] >= 1
        dlq_payloads = fake_client.queue_snapshot(diag["dead_letter_queue_name"])
        assert len(dlq_payloads) >= 1
    finally:
        runner.stop()


def test_redis_job_runner_lists_and_requeues_dead_letters():
    fake_client = _FakeRedisClient()
    seen = {"calls": 0}

    def _fail_once_then_succeed(value: int) -> None:
        seen["calls"] += 1
        if seen["calls"] == 1:
            raise RuntimeError("first call fails")
        _redis_test_task(value)

    with _REDIS_OBSERVED_LOCK:
        _REDIS_TEST_OBSERVED.clear()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:dlq-requeue",
        pop_timeout_seconds=0.1,
        max_attempts=1,
        redis_client_factory=lambda _url: fake_client,
    )
    try:
        assert runner.submit(_fail_once_then_succeed, 21) is True
        assert _wait_until(lambda: runner.diagnostics()["dead_lettered_count"] >= 1, timeout_s=2.0)
        listed = runner.list_dead_letters(limit=5)
        assert listed["dead_letter_queue_size"] >= 1
        assert listed["items"]
        first = listed["items"][0]
        assert first.get("reason") == "task_execution_error"
        assert first.get("task_name")

        requeued = runner.requeue_dead_letters(limit=1)
        assert requeued["affected_count"] == 1
        assert _wait_until(lambda: _REDIS_TEST_OBSERVED == [21], timeout_s=2.0)
        diag = runner.diagnostics()
        assert diag["requeued_count"] >= 1
    finally:
        runner.stop()


def test_redis_job_runner_purges_dead_letters():
    fake_client = _FakeRedisClient()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:dlq-purge",
        pop_timeout_seconds=0.1,
        redis_client_factory=lambda _url: fake_client,
    )
    try:
        fake_client.rpush(runner.dead_letter_queue_name, '{"reason":"one"}')
        fake_client.rpush(runner.dead_letter_queue_name, '{"reason":"two"}')
        listed = runner.list_dead_letters(limit=10)
        assert listed["dead_letter_queue_size"] == 2
        purge = runner.purge_dead_letters(limit=1)
        assert purge["affected_count"] == 1
        listed_after = runner.list_dead_letters(limit=10)
        assert listed_after["dead_letter_queue_size"] == 1
    finally:
        runner.stop()


def test_redis_job_runner_dead_letter_includes_dispatch_and_metadata():
    fake_client = _FakeRedisClient()

    def _always_fail_job(job_id: str) -> None:
        raise RuntimeError(f"boom for {job_id}")

    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:metadata",
        pop_timeout_seconds=0.1,
        max_attempts=1,
        redis_client_factory=lambda _url: fake_client,
    )
    try:
        assert runner.submit(_always_fail_job, "job-meta-1") is True
        assert _wait_until(lambda: runner.diagnostics()["dead_lettered_count"] >= 1, timeout_s=2.0)
        listed = runner.list_dead_letters(limit=5)
        assert listed["items"]
        item = listed["items"][0]
        assert item.get("dispatch_id")
        assert item.get("job_id") == "job-meta-1"
        assert isinstance(item.get("metadata"), dict)
        assert item["metadata"]["job_id"] == "job-meta-1"
        assert item.get("failed_at") is not None
        assert item.get("first_failed_at") is not None
    finally:
        runner.stop()


def test_redis_job_runner_requeue_preserves_metadata_from_wrapped_dead_letter_payload():
    fake_client = _FakeRedisClient()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:wrapped",
        pop_timeout_seconds=0.1,
        max_attempts=2,
        redis_client_factory=lambda _url: fake_client,
        consumer_enabled=False,
    )
    try:
        wrapped = {
            "task_name": "grantflow.tests.test_job_runner:_redis_test_task",
            "reason": "task_execution_error",
            "dispatch_id": "dispatch-123",
            "metadata": {"job_id": "job-wrapped-1"},
            "payload": {
                "task_name": "grantflow.tests.test_job_runner:_redis_test_task",
                "args": [99],
                "kwargs": {},
                "attempt": 1,
                "max_attempts": 2,
            },
        }
        fake_client.rpush(runner.dead_letter_queue_name, json.dumps(wrapped, ensure_ascii=True))
        result = runner.requeue_dead_letters(limit=1)
        assert result["affected_count"] == 1
        queued = fake_client.queue_snapshot(runner.queue_name)
        assert len(queued) == 1
        payload = json.loads(queued[0])
        assert payload["dispatch_id"] == "dispatch-123"
        assert payload["metadata"]["job_id"] == "job-wrapped-1"
    finally:
        runner.stop()


def test_redis_job_runner_worker_heartbeat_status_for_dispatcher_mode():
    fake_client = _FakeRedisClient()
    runner = RedisJobRunner(
        worker_count=1,
        queue_maxsize=8,
        redis_url="redis://local-test/0",
        queue_name="grantflow:test:jobs:hb-status",
        pop_timeout_seconds=0.1,
        redis_client_factory=lambda _url: fake_client,
        consumer_enabled=False,
    )
    try:
        before = runner.worker_heartbeat_status()
        assert before["present"] is False
        assert before["healthy"] is False

        assert runner.touch_worker_heartbeat(source="test-worker") is True
        after = runner.worker_heartbeat_status()
        assert after["present"] is True
        assert after["healthy"] is True
        assert after["source"] == "test-worker"
        diag = runner.diagnostics()
        assert diag["worker_heartbeat"]["healthy"] is True
    finally:
        runner.stop()
