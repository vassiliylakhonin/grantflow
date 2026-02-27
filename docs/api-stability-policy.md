# Public API Stability Policy

## Scope

This policy applies to public HTTP endpoints documented in `README.md` and OpenAPI (`/openapi.json`), including:

- endpoint paths and methods
- request/response field names and basic types
- status semantics (`accepted`, `running`, `pending_hitl`, `done`, `error`, `canceled`)

Runtime version source of truth is `grantflow/core/version.py`.

## Stability Levels

### Stable

Endpoints under active production usage and documented in README.

Rules:

- additive changes are allowed (new optional fields, new endpoints)
- removing/renaming fields is breaking
- changing meaning of existing fields is breaking

### Experimental

New endpoints/fields can be marked experimental in README before stabilization.

Rules:

- may change faster, but should keep best-effort backward compatibility
- must be clearly labeled as experimental

## Versioning and Breakage

GrantFlow uses SemVer:

- `MAJOR`: breaking API changes
- `MINOR`: backward-compatible feature additions
- `PATCH`: backward-compatible fixes

Breaking API changes require all of:

- SemVer major bump
- changelog migration notes
- PR reviewer acknowledgment of breaking scope

## Deprecation Window

For stable endpoints/fields:

- announce deprecation in `CHANGELOG.md` and README
- keep deprecated behavior for at least one minor release where feasible
- include migration path before removal

## Compatibility Expectations

- Clients should tolerate unknown fields in responses.
- Server should preserve existing required fields for stable endpoints.
- Existing success/error status codes should remain consistent unless explicitly version-bumped.
- Golden contract fixtures in `grantflow/tests/fixtures/` should be updated only when intended API behavior changes.
