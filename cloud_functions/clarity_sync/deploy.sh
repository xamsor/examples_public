#!/bin/bash
# Deploy Clarity Sync Cloud Function
#
# Prerequisites:
# 1. gcloud CLI installed and authenticated
# 2. APIs enabled (see below)
# 3. Environment variables set

set -e

# Configuration
PROJECT_ID="getlinkspro-453615"
REGION="us-central1"
FUNCTION_NAME="clarity-sync"
DATASET_NAME="clarity"

echo "=============================================="
echo "Deploying Clarity Sync Cloud Function"
echo "=============================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Function: $FUNCTION_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable bigquery.googleapis.com

# Create BigQuery dataset if it doesn't exist
echo ""
echo "Creating BigQuery dataset '$DATASET_NAME' if needed..."
bq --project_id=$PROJECT_ID mk --dataset --location=US $PROJECT_ID:$DATASET_NAME 2>/dev/null || echo "Dataset already exists"

# Check for Clarity token
if [ -z "$CLARITY_API_TOKEN" ]; then
    echo ""
    echo "ERROR: CLARITY_API_TOKEN environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export CLARITY_API_TOKEN='your-token-here'"
    echo ""
    echo "Or load from .env:"
    echo "  source <(grep CLARITY .env | sed 's/^/export /')"
    exit 1
fi

# Deploy function
echo ""
echo "Deploying Cloud Function..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python312 \
    --region=$REGION \
    --source=. \
    --entry-point=sync_clarity \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256MB \
    --timeout=120s \
    --set-env-vars="CLARITY_API_TOKEN=$CLARITY_API_TOKEN,CLARITY_PROJECT_ID=${CLARITY_PROJECT_ID:-pf8kyjwawu},GCP_PROJECT_ID=$PROJECT_ID,BQ_DATASET=$DATASET_NAME"

# Get function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --gen2 --format='value(serviceConfig.uri)')

echo ""
echo "Function deployed successfully!"
echo "URL: $FUNCTION_URL"

# Create Cloud Scheduler job
echo ""
echo "Creating Cloud Scheduler job (daily at 6 AM UTC)..."
gcloud scheduler jobs delete clarity-daily-sync --location=$REGION --quiet 2>/dev/null || true

gcloud scheduler jobs create http clarity-daily-sync \
    --location=$REGION \
    --schedule="0 6 * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --message-body='{"days": 3}' \
    --headers="Content-Type=application/json" \
    --time-zone="UTC" \
    --description="Daily Clarity data sync to BigQuery"

echo ""
echo "=============================================="
echo "DEPLOYMENT COMPLETE"
echo "=============================================="
echo ""
echo "Cloud Function URL: $FUNCTION_URL"
echo "Scheduler: Daily at 6:00 AM UTC"
echo "BigQuery dataset: $PROJECT_ID.$DATASET_NAME"
echo ""
echo "To test manually:"
echo "  curl -X POST $FUNCTION_URL"
echo ""
echo "To check logs:"
echo "  gcloud functions logs read $FUNCTION_NAME --region=$REGION --gen2"
echo ""
echo "To view data in BigQuery:"
echo "  bq query --project_id=$PROJECT_ID 'SELECT * FROM $DATASET_NAME.snapshots ORDER BY snapshot_time DESC LIMIT 5'"
