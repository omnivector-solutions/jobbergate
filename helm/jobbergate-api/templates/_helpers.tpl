{{/*
S3-compatible object storage env vars for the jobbergate-api and migration
containers. Shared between deploy.yaml and db_cleanup.yaml so the
garage/s3 branching only needs to be written once.
*/}}
{{- define "jobbergate-api.s3Env" -}}
{{- if not (has .Values.storage.backend (list "garage" "s3")) }}
{{- fail (printf "storage.backend must be \"garage\" or \"s3\", got %q (the \"minio\" backend was replaced by \"garage\")" .Values.storage.backend) }}
{{- end }}
- name: S3_BUCKET_NAME
  value: {{ .Values.storage.bucketName | quote }}
{{- if eq .Values.storage.backend "garage" }}
- name: S3_ENDPOINT_URL
  value: http://jobbergate-garage:3900
- name: AWS_DEFAULT_REGION
  value: {{ .Values.storage.garage.region | quote }}
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      key: GARAGE_DEFAULT_ACCESS_KEY
      name: jobbergate-garage-credentials
      optional: false
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      key: GARAGE_DEFAULT_SECRET_KEY
      name: jobbergate-garage-credentials
      optional: false
{{- else }}
{{- with .Values.storage.s3.endpointUrl }}
- name: S3_ENDPOINT_URL
  value: {{ . | quote }}
{{- end }}
{{- with .Values.storage.s3.region }}
- name: AWS_DEFAULT_REGION
  value: {{ . | quote }}
{{- end }}
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.storage.s3.existingSecret | default "jobbergate-s3-credentials" }}
      key: {{ .Values.storage.s3.existingSecretAccessKeyIdKey }}
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.storage.s3.existingSecret | default "jobbergate-s3-credentials" }}
      key: {{ .Values.storage.s3.existingSecretSecretAccessKeyKey }}
{{- end }}
{{- end -}}

{{/*
Database environment shared by the jobbergate-api container and the migration
init container. DATABASE_HOST comes from the jobbergate-api ConfigMap.
DATABASE_NAME is only set when multi-tenancy is disabled. With multi-tenancy,
the database is selected per request from the organization id in the token.
*/}}
{{- define "jobbergate-api.dbEnv" -}}
- name: MULTI_TENANCY_ENABLED
  value: {{ .Values.multiTenancy.enabled | quote }}
{{- if not .Values.multiTenancy.enabled }}
- name: DATABASE_NAME
  value: {{ .Values.postgres.database | quote }}
{{- end }}
- name: DATABASE_USER
  value: omnivector
- name: DATABASE_PSWD
  valueFrom:
    secretKeyRef:
      name: jobbergate-kubegres-credentials
      key: primary-password
- name: DATABASE_PORT
  value: "5432"
{{- end }}

{{/*
Garage configuration (/etc/garage.toml). Secrets (rpc secret, S3 key) are not
part of this file, they are injected through GARAGE_* environment variables.
*/}}
{{- define "jobbergate-api.garageConfig" -}}
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"
db_engine = "sqlite"
replication_factor = 1
rpc_bind_addr = "0.0.0.0:3901"

[s3_api]
api_bind_addr = "0.0.0.0:3900"
s3_region = {{ .Values.storage.garage.region | quote }}
{{- end }}
