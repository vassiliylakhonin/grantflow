# Container Hardening Runbook

Operational baseline for secure-by-default container deployment of GrantFlow.

## Baseline controls

For API and worker containers:
- run as non-root (`appuser`, UID 10001)
- read-only root filesystem (`read_only: true`)
- writable state only in mounted volume (`/data`)
- ephemeral tmp space via `tmpfs` (`/tmp`)
- Linux privilege escalation disabled (`no-new-privileges:true`)
- all Linux capabilities dropped (`cap_drop: [ALL]`)

For supporting services:
- Redis and Chroma bind to localhost by default in compose
- Redis starts with `--protected-mode yes`

## Validation commands

```bash
docker compose -f docker-compose.pilot.yml config >/tmp/grantflow-compose.rendered.yml
docker compose -f docker-compose.pilot.yml up -d
```

Check effective runtime user:

```bash
docker inspect grantflow_api --format '{{.Config.User}}'
docker inspect grantflow_worker --format '{{.Config.User}}'
```

Check read-only rootfs and security options:

```bash
docker inspect grantflow_api --format '{{.HostConfig.ReadonlyRootfs}}'
docker inspect grantflow_api --format '{{json .HostConfig.SecurityOpt}}'
docker inspect grantflow_api --format '{{json .HostConfig.CapDrop}}'
```

Check localhost port bindings:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

## Safe exceptions process

If a service requires additional write paths or capabilities:
1. Add minimal, explicit exception in compose.
2. Add a comment with reason + owner + expiry date.
3. Add a follow-up issue to remove exception.
4. Re-run security workflow and smoke tests.

## Patch/rebuild process

1. Pull latest base image updates.
2. Rebuild container image.
3. Run local Trivy image scan.
4. Deploy to staging.
5. Verify `/health` and `/ready`.
6. Promote to production.

## Known limitations

- Container hardening does not replace host-level controls.
- Network segmentation, secrets management, TLS, and backup strategy must be handled by platform ops.
