# timescaledb-cnpg

PostgreSQL image for [CloudNativePG](https://cloudnative-pg.io/), based on the official
`ghcr.io/cloudnative-pg/postgresql` image with the
[TimescaleDB](https://www.timescale.com/) extension installed. Used by the
`jobbergate-api` Helm chart's `Cluster` resource to support the hypertables and
continuous aggregates created by its job metrics migrations.

## Build and publish

No CI workflow builds this image; it is published manually when `Dockerfile` changes
(e.g. a new PostgreSQL or TimescaleDB release).

```bash
docker build \
  --build-arg PG_MAJOR=17 \
  -t ghcr.io/omnivector-solutions/timescaledb-cnpg:17 \
  containers/timescaledb-cnpg

docker push ghcr.io/omnivector-solutions/timescaledb-cnpg:17
```

Tag the image after the PostgreSQL major version it is built from (e.g. `17`), matching
the tag scheme the Helm chart's `postgres.image` value expects.
