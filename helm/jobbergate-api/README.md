# jobbergate-api Helm Chart

Deploys the Jobbergate API standalone, with its own:

- Postgres (TimescaleDB) database via [CloudNativePG](https://cloudnative-pg.io/).
  CloudNativePG generates and stores its own app credentials (no External Secrets
  needed for the database); optional continuous backup to S3 is available via
  `postgres.backup.*`.
- Object storage for job scripts and templates, either:
  - **Garage** (default, `storage.backend: garage`): the chart deploys its own
    single-node [Garage](https://garagehq.deuxfleurs.fr/) instance (Deployment, PVC,
    Service, generated credentials). Garage creates the bucket and the S3 key by
    itself on first start, or
  - **S3** (`storage.backend: s3`): no Garage is deployed; the API is pointed at an
    external bucket (AWS S3, or any S3-compatible service) using credentials you
    provide via `storage.s3.*` (either inline, or an existing Secret).

This chart makes no assumptions about your cloud provider or cluster setup: it has no
hardcoded node affinity, no cloud-specific Ingress annotations, and no proprietary
add-ons. Everything infrastructure-specific (storage class, ingress class/annotations,
scheduling, image pull secrets) is left to `values.yaml` for you to fill in.

## Requirements

- A cluster with the [CloudNativePG operator](https://cloudnative-pg.io/) installed
  (CRD `postgresql.cnpg.io/v1`).
- [External Secrets Operator](https://external-secrets.io/) with a `ClusterSecretStore`
  (name configurable via `externalSecrets.clusterSecretStoreName`), required only when
  `storage.backend: garage` (the default), to back the `Password` generator used for
  Garage's credentials.
- An OIDC provider (Keycloak, Auth0, etc) to issue the JWTs Jobbergate validates.

## External dependencies (not deployed by this chart)

- CloudNativePG operator (CRD `postgresql.cnpg.io/v1`).
- `ClusterSecretStore` (default name `k8s-secretsmanager`, configurable) for the
  External Secrets Operator, only needed when `storage.backend: garage`.
- RabbitMQ (optional, disabled by default via `rabbitmq.enabled: false`): used only to
  publish job submission status change notifications; the API works fine without it.
  When enabled, defaults assume a sibling install of the
  [Bitnami RabbitMQ chart](https://github.com/bitnami/charts/tree/main/bitnami/rabbitmq)
  named `rabbitmq` (Service `rabbitmq`, Secret `rabbitmq-default-user`). Override
  `rabbitmq.*` in `values.yaml` if yours is named differently.

## Install

```bash
helm install jobbergate-api ./helm/jobbergate-api -f my-values.yaml
```

Or straight from GHCR (see Publishing below):

```bash
helm install jobbergate-api oci://ghcr.io/omnivector-solutions/charts/jobbergate-api --version <chart-version>
```

At minimum, set `auth.armasecDomain` to your OIDC realm (e.g.
`keycloak.example.com/realms/jobbergate`).

See `values.yaml` for all configurable options: image, resources, scheduling
(`affinity`/`tolerations`/`nodeSelector`), autoscaling, ingress, Sentry, RabbitMQ
(optional, `rabbitmq.enabled`), storage backend (`storage.backend: garage|s3`),
storage class, and the periodic auto-clean job.

## Multi-tenancy

Multi-tenancy is **disabled by default** (`multiTenancy.enabled: false`).

- **Disabled:** Jobbergate uses a single database, named by `postgres.database` (default
  `jobbergate`). The same value is used for the database CloudNativePG bootstraps and for
  the `DATABASE_NAME` passed to the API, so they always match.
- **Enabled:** Jobbergate selects the database per request from the organization id in
  the user's token, and `DATABASE_NAME` is not set. Tenant databases must already exist,
  named after the organization id (UUID).

```yaml
multiTenancy:
  enabled: true
```

The migration init container and the auto-clean CronJob follow this setting: they act
on the single database when multi-tenancy is disabled, and on every database whose
name is a UUID when it is enabled.

With multi-tenancy enabled, each tenant also uses its own **bucket**, named after the
organization id. The chart only creates the bucket set in `storage.bucketName`, so tenant
buckets must be provisioned (like the tenant databases). With the Garage backend:

```bash
KEY=$(kubectl get secret jobbergate-garage-credentials -o jsonpath='{.data.GARAGE_DEFAULT_ACCESS_KEY}' | base64 -d)
kubectl exec deploy/jobbergate-garage -- /garage bucket create <organization-id>
kubectl exec deploy/jobbergate-garage -- /garage bucket allow --read --write --owner <organization-id> --key "$KEY"
```

## Postgres

CloudNativePG creates the `jobbergate-postgres` Cluster and a `jobbergate-postgres-app`
Secret holding the generated `username`/`password` for the database owner
(`postgres.owner`, default `jobbergate`); the API and the migration/cleanup jobs read
their credentials from that Secret. `postgres.highAvailability: true` (default) runs 2
instances (1 primary + 1 standby) with pod anti-affinity; set it to `false` for a single
instance.

The default `postgres.image` (`ghcr.io/omnivector-solutions/timescaledb-cnpg`) is the
official CloudNativePG PostgreSQL image with the TimescaleDB extension installed (built
from `containers/timescaledb-cnpg` in this repository), needed for the job metrics
hypertables and continuous aggregates created by the API's migrations. Point
`postgres.image` elsewhere if you build or source your own.

Continuous backup is **disabled by default**. Set `postgres.backup.enabled: true` and
provide a bucket plus credentials (`postgres.backup.destinationPath`,
`accessKeyId`/`secretAccessKey` or `existingSecret`) to enable it; this chart does not
provision the bucket itself. It uses CloudNativePG's native Barman Cloud integration,
which upstream has deprecated in favor of the separate Barman Cloud Plugin (removal
planned for CloudNativePG 1.28); this chart will move to the plugin before that happens.

### Database migrations

An init container (`migration`) runs `alembic upgrade head` before the API starts, after
the `pgchecker` init container confirms Postgres is reachable. The script is shipped in
the `check-migration` ConfigMap.

## Object storage

With `storage.backend: garage` (default), the chart deploys a single-node Garage
instance and passes the endpoint (`http://jobbergate-garage:3900`), bucket
(`storage.bucketName`), region (`storage.garage.region`) and generated credentials to
the API. Garage keeps its metadata and data in one PVC (`storage.garage.storageSize`).

With `storage.backend: s3`, nothing is deployed for storage, and the API uses the
endpoint, region and credentials from `storage.s3.*`.

### Upgrading from MinIO

The `minio` backend was removed. Setting `storage.backend: minio` fails the render with an
explicit error. The chart does **not** migrate existing objects: the Garage bucket starts
empty.

**`helm upgrade` deletes the MinIO resources, including its PersistentVolumeClaim
(`minio-pvc`), which removes the stored objects if the volume reclaim policy is `Delete`.**
Before upgrading, copy the objects from the MinIO bucket to a safe place (for example with
`rclone` or `mc mirror`), and restore them into the new Garage bucket afterwards. To keep
using MinIO instead, run it yourself and set `storage.backend: s3` with
`storage.s3.endpointUrl`.

## Publishing (CI)

- **Container image** (`.github/workflows/publish_on_tag.yaml`): the `publish-to-ghcr`
  job builds and pushes `jobbergate-api`, `jobbergate-cli` and `jobbergate-agent`
  images to [GHCR](https://ghcr.io/omnivector-solutions), tagged by
  `docker/metadata-action` with the semver version, `{major}.{minor}`, `{major}`, the
  git ref and the commit SHA; the `publish-to-ecr` job additionally pushes
  `jobbergate-api`'s image to Amazon ECR. Both run on every app version tag.
- **Helm chart** (`.github/workflows/publish_jobbergate_api_helm_chart.yaml`): packaged
  from this directory and pushed as an OCI artifact to
  `oci://ghcr.io/omnivector-solutions/charts/jobbergate-api` whenever a
  `jobbergate-api-chart-v<Chart.yaml version>` tag is pushed (versioned independently
  from the app), or via manual dispatch. The chart's `version` in `Chart.yaml` must
  match the tag.

To release a new chart version: bump `version` in `Chart.yaml`, merge, then tag
`jobbergate-api-chart-v<version>` (e.g. `jobbergate-api-chart-v0.2.0`) and push the tag.
