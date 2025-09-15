#!/bin/bash

# GCP APIs有効化スクリプト
# Auto Remediation System用

set -e

PROJECT_ID=${1:-$GOOGLE_CLOUD_PROJECT}

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: PROJECT_ID is required"
    echo "Usage: $0 <PROJECT_ID>"
    echo "Or set GOOGLE_CLOUD_PROJECT environment variable"
    exit 1
fi

echo "🚀 Enabling GCP APIs for project: $PROJECT_ID"

# 必須APIs
APIS=(
    "aiplatform.googleapis.com"          # Vertex AI
    "monitoring.googleapis.com"          # Cloud Monitoring
    "logging.googleapis.com"             # Cloud Logging
    "sqladmin.googleapis.com"            # Cloud SQL Admin
    "sql-component.googleapis.com"       # Cloud SQL
    "secretmanager.googleapis.com"       # Secret Manager
    "firebase.googleapis.com"            # Firebase
    "identitytoolkit.googleapis.com"     # Firebase Auth
    "run.googleapis.com"                 # Cloud Run
    "cloudbuild.googleapis.com"          # Cloud Build
    "containerregistry.googleapis.com"   # Container Registry
    "cloudscheduler.googleapis.com"      # Cloud Scheduler
)

echo "📋 APIs to enable:"
for api in "${APIS[@]}"; do
    echo "  - $api"
done

echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "⚡ Enabling APIs..."

for api in "${APIS[@]}"; do
    echo "🔧 Enabling $api..."
    gcloud services enable "$api" --project="$PROJECT_ID"

    if [ $? -eq 0 ]; then
        echo "✅ $api enabled successfully"
    else
        echo "❌ Failed to enable $api"
        exit 1
    fi
done

echo ""
echo "🎉 All APIs enabled successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Create service account: gcloud iam service-accounts create auto-remediation-sa"
echo "2. Assign necessary roles"
echo "3. Generate service account key"
echo "4. Set GOOGLE_APPLICATION_CREDENTIALS environment variable"
