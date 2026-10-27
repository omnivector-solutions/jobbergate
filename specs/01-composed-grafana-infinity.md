# Spec 1 — Grafana + Infinity in jobbergate-composed

## Goal

Let a developer see the metrics/analytics loop end to end locally: Grafana (with the
Infinity datasource plugin) reads the Jobbergate API's `/analytics/*` JSON endpoints
over OAuth2 client credentials, exactly as the on-prem stack will in production.

## Non-goals

- No VictoriaMetrics/vmagent in composed (scrape path is exercised in real deployments).
- No production-grade Grafana auth; anonymous admin is fine for local dev.

## Changes

### `jobbergate-composed/docker-compose.yml`

New service `grafana` under a dedicated profile so it is **not** started by default:

- `image: grafana/grafana-oss:11.4.0`, `profiles: ["observability"]`, port `3000:3000`.
- `GF_INSTALL_PLUGINS=yesoreyeram-infinity-datasource` (downloaded at container start;
  requires internet access, acceptable for dev).
- Anonymous access enabled with `Admin` org role (no login friction locally).
- Volumes: `grafana_data` named volume + `./etc/grafana/provisioning` mounted at
  `/etc/grafana/provisioning` (read-only).
- `depends_on: jobbergate-api (healthy), keycloak.local (healthy)`.

Start with: `docker compose --profile observability up grafana`.

### Provisioning files (`jobbergate-composed/etc/grafana/`)

- `provisioning/datasources/jobbergate.yaml` — Infinity datasource
  (`type: yesoreyeram-infinity-datasource`, uid `jobbergate-infinity`) configured with
  OAuth2 client credentials: token URL
  `http://keycloak.local:8080/realms/jobbergate-local/protocol/openid-connect/token`,
  client `local-slurm` + its composed secret, `allowedHosts: [http://jobbergate-api:80]`.
- `provisioning/dashboards/jobbergate.yaml` — file provider pointing at
  `/etc/grafana/provisioning/dashboards`.
- `provisioning/dashboards/jobbergate-analytics.json` — starter dashboard with two
  table panels backed by the Infinity datasource:
  - Template usage: `GET /jobbergate/analytics/templates?start_time=${__from:date:iso}&end_time=${__to:date:iso}&interval=day`, root selector `items`.
  - Submission statuses: same pattern against `/jobbergate/analytics/submissions`.

### Keycloak realm (`jobbergate-composed/etc/jobbergate-local.json`)

The analytics endpoints require `jobbergate:admin` or `jobbergate:metrics:read`.
`service-account-local-slurm` has neither today, so:

- Add a `jobbergate:metrics:read` client role to the `local-slurm` and `cli` clients.
- Grant it to `service-account-local-slurm` (Grafana's token) — `local-user` already
  holds `jobbergate:admin`, so the CLI works unchanged.

Caveat: the realm is imported only when the `kc-realm-files` volume is first created;
existing dev environments need `docker compose down -v` (or manual role creation) to
pick this up.

## Acceptance

- `docker compose up` (no profile) behaves exactly as before — Grafana absent.
- `docker compose --profile observability up -d grafana` → http://localhost:3000 opens
  without login, the Jobbergate datasource passes "Save & test", and both dashboard
  panels render rows once submissions exist.
