# Coverage Threshold Policy

This repository uses a **pragmatic threshold policy** focused on core-path confidence over vanity percentages.

## Policy

- Do not merge changes that reduce confidence on critical paths without compensating tests.
- For changes touching core pipeline/API/export logic, add or update targeted tests.
- Use contract tests + integration smoke + eval suites as the primary confidence stack.

## Threshold Direction

- Baseline target: maintain or improve effective coverage on critical modules.
- Hard global numeric fail-under is deferred until coverage collection is fully deterministic in CI for all suites.

## Merge Gate Expectations (current)

- CI test jobs must pass.
- Contract guards must pass.
- Quality/eval guards must pass.
- For risky changes, include explicit test evidence in PR summary.

## Future Tightening (planned)

- Introduce module-level thresholds for core packages once stable coverage telemetry is consistently available in CI artifacts.
