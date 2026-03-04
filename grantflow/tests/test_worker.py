from grantflow import worker as worker_module


def test_worker_requires_redis_queue_mode(monkeypatch):
    monkeypatch.setattr(worker_module.config.job_runner, "mode", "background_tasks")
    assert worker_module.main() == 2


def test_worker_builds_redis_runner_with_consumer_enabled(monkeypatch):
    monkeypatch.setattr(worker_module.config.job_runner, "worker_count", 3)
    monkeypatch.setattr(worker_module.config.job_runner, "queue_maxsize", 222)
    monkeypatch.setattr(worker_module.config.job_runner, "redis_url", "redis://127.0.0.1:6379/9")
    monkeypatch.setattr(worker_module.config.job_runner, "redis_queue_name", "grantflow:test:jobs")
    monkeypatch.setattr(worker_module.config.job_runner, "redis_pop_timeout_seconds", 0.5)
    monkeypatch.setattr(worker_module.config.job_runner, "redis_max_attempts", 5)
    monkeypatch.setattr(worker_module.config.job_runner, "redis_dead_letter_queue_name", "grantflow:test:jobs:dead")

    runner = worker_module._build_redis_worker_runner()
    diag = runner.diagnostics()
    assert diag["backend"] == "redis"
    assert diag["consumer_enabled"] is True
    assert diag["worker_count"] == 3
    assert diag["queue_maxsize"] == 222
    assert diag["queue_name"] == "grantflow:test:jobs"
    assert diag["max_attempts"] == 5
    assert diag["dead_letter_queue_name"] == "grantflow:test:jobs:dead"
