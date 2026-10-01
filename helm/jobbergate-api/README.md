# jobbergate-api Helm Chart

Deploys the Jobbergate API standalone, with its own:

- Postgres (TimescaleDB) database via [Kubegres](https://www.kubegres.io/), including
  backup PVC, replica/primary credentials generated through
  [External Secrets](https://external-secrets.io/), and the continuous aggregate
  refresh CronJobs.
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

- A running Postgres-capable cluster with the [Kubegres operator](https://www.kubegres.io/)
  installed.
- [External Secrets Operator](https://external-secrets.io/) with a `ClusterSecretStore`
  (name configurable via `externalSecrets.clusterSecretStoreName`) able to back the
  `Password` generator used for DB credentials, and Garage credentials when
  `storage.backend: garage` (the default).
- An external RabbitMQ instance (see below).
- An OIDC provider (Keycloak, Auth0, etc) to issue the JWTs Jobbergate validates.

## External dependencies (not deployed by this chart)

- `ClusterSecretStore` (default name `k8s-secretsmanager`, configurable) for the
  External Secrets Operator.
- Kubegres operator (CRD `kubegres.reactive-tech.io/v1`).
- RabbitMQ: defaults assume a sibling install of the
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
(`affinity`/`tolerations`/`nodeSelector`), autoscaling, ingress, Sentry, RabbitMQ,
storage backend (`storage.backend: garage|s3`), storage class, and the periodic
auto-clean job.

## Multi-tenancy

Multi-tenancy is **disabled by default** (`multiTenancy.enabled: false`).

- **Disabled:** Jobbergate uses a single database, named by `postgres.database` (default
  `jobbergate`). The same value is used for the `POSTGRES_DB` created by Kubegres and for
  the `DATABASE_NAME` passed to the API, so they always match.
- **Enabled:** Jobbergate selects the database per request from the organization id in
  the user's token, and `DATABASE_NAME` is not set. Tenant databases must already exist,
  named after the organization id (UUID).

```yaml
multiTenancy:
  enabled: true
```

The migration init container, the continuous aggregate CronJobs and the auto-clean
CronJob follow this setting: they act on the single database when multi-tenancy is
disabled, and on every database whose name is a UUID when it is enabled.

With multi-tenancy enabled, each tenant also uses its own **bucket**, named after the
organization id. The chart only creates the bucket set in `storage.bucketName`, so tenant
buckets must be provisioned (like the tenant databases). With the Garage backend:

```bash
KEY=$(kubectl get secret jobbergate-garage-credentials -o jsonpath='{.data.GARAGE_DEFAULT_ACCESS_KEY}' | base64 -d)
kubectl exec deploy/jobbergate-garage -- /garage bucket create <organization-id>
kubectl exec deploy/jobbergate-garage -- /garage bucket allow --read --write --owner <organization-id> --key "$KEY"
```

## Database migrations

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
