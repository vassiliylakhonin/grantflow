__all__ = [
    "load_eval_cases",
    "run_eval_case",
    "run_eval_suite",
    "format_eval_suite_report",
]


def __getattr__(name: str):
    if name in __all__:
        from grantflow.eval import harness

        return getattr(harness, name)
    raise AttributeError(name)
