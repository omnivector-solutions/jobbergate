# jobbergate-api Helm Chart

Deploys the Jobbergate API standalone, with its own:

- Postgres (TimescaleDB) database via [Kubegres](https://www.kubegres.io/), including
  backup PVC, replica/primary credentials generated through
  [External Secrets](https://external-secrets.io/), and the continuous aggregate
  refresh CronJobs.
- Object storage for job scripts and templates, either:
  - **MinIO** (default, `storage.backend: minio`): the chart deploys its own MinIO
    instance (Deployment, PVC, Service, generated credentials), or
  - **S3** (`storage.backend: s3`): no MinIO is deployed; the API is pointed at an
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
  `Password` generator used for DB credentials, and MinIO credentials when
  `storage.backend: minio` (the default).
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
storage backend (`storage.backend: minio|s3`), storage class, and the periodic
auto-clean job.

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
