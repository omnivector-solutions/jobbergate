{{/*
S3-compatible object storage env vars for the jobbergate-api and migration
containers. Shared between deploy.yaml and db_cleanup.yaml so the
minio/s3 branching only needs to be written once.
*/}}
{{- define "jobbergate-api.s3Env" -}}
- name: S3_BUCKET_NAME
  value: {{ .Values.storage.bucketName | quote }}
{{- if eq .Values.storage.backend "minio" }}
- name: S3_ENDPOINT_URL
  value: http://jobbergate-minio:9000
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      key: MINIO_ACCESS_KEY
      name: jobbergate-minio-credentials
      optional: false
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      key: MINIO_SECRET_KEY
      name: jobbergate-minio-credentials
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
