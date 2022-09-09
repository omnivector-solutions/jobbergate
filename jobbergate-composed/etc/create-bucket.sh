#!/bin/bash
set -e

mc alias set myminio http://minio:9000 compose-s3-key compose-s3-secret
mc mb myminio/jobbergate-resources
mc policy set public myminio/jobbergate-resources
