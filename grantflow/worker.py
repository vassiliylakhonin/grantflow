from __future__ import annotations

import signal
import threading

from grantflow.core.config import config
from grantflow.core.job_runner import RedisJobRunner


def _build_redis_worker_runner() -> RedisJobRunner:
    return RedisJobRunner(
        worker_count=int(getattr(config.job_runner, "worker_count", 2) or 2),
        queue_maxsize=int(getattr(config.job_runner, "queue_maxsize", 200) or 200),
        redis_url=str(getattr(config.job_runner, "redis_url", "redis://127.0.0.1:6379/0") or ""),
        queue_name=str(getattr(config.job_runner, "redis_queue_name", "grantflow:jobs") or ""),
        pop_timeout_seconds=float(getattr(config.job_runner, "redis_pop_timeout_seconds", 1.0) or 1.0),
        consumer_enabled=True,
    )


def main() -> int:
    mode = str(getattr(config.job_runner, "mode", "background_tasks") or "background_tasks").strip().lower()
    if mode != "redis_queue":
        print(
            "grantflow.worker requires GRANTFLOW_JOB_RUNNER_MODE=redis_queue " f"(current={mode or 'unknown'})",
            flush=True,
        )
        return 2

    runner = _build_redis_worker_runner()
    shutdown_requested = threading.Event()

    def _request_shutdown(_signum, _frame) -> None:
        shutdown_requested.set()

    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    runner.start()
    diag = runner.diagnostics()
    print(
        "GrantFlow Redis worker started "
        f"(workers={diag.get('worker_count')}, queue={diag.get('queue_name')}, redis={diag.get('redis_url')})",
        flush=True,
    )
    try:
        while not shutdown_requested.wait(1.0):
            pass
    finally:
        runner.stop()
        print("GrantFlow Redis worker stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
