#!/bin/bash
# Deploys the SRE Guardian (Incident-2277) Live Transaction Inspector UX to Cloud Run.
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT to your GCP project ID}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DATASET_ID="${BIGQUERY_DATASET:-sre_workshop}"
AGENT_ENGINE_ID="${VERTEX_AGENT_ENGINE_ID:-0000000000000000000}"
SERVICE_NAME="${SERVICE_NAME:-sre-guardian-ux}"

gcloud run deploy "${SERVICE_NAME}" \
  --source=. \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},BIGQUERY_DATASET=${DATASET_ID},VERTEX_AGENT_ENGINE_ID=${AGENT_ENGINE_ID}"
