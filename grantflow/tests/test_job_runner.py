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
