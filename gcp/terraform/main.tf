# Auto Remediation System - GCP Infrastructure
# Terraform設定ファイル

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
  }

  backend "gcs" {
    bucket = "auto-remediation-terraform-state"
    prefix = "terraform/state"
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "prod"
}

variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
}

variable "slack_bot_token" {
  description = "Slack Bot Token"
  type        = string
  sensitive   = true
}

variable "firebase_config" {
  description = "Firebase Configuration JSON"
  type        = string
  sensitive   = true
}

# Provider設定
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# APIs有効化
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "sql.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "aiplatform.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ])

  service = each.key
  project = var.project_id

  disable_on_destroy = false
}

# Cloud SQL - PostgreSQL
resource "google_sql_database_instance" "postgres" {
  name             = "auto-remediation-db-${var.environment}"
  database_version = "POSTGRES_14"
  region          = var.region

  settings {
    tier              = "db-custom-2-4096"
    availability_type = "REGIONAL"
    disk_type         = "PD_SSD"
    disk_size         = 100
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                    = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.vpc.id
      require_ssl     = true

      authorized_networks {
        name  = "cloud-run"
        value = "0.0.0.0/0"
      }
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }
  }

  depends_on = [google_project_service.apis]
}

# データベース作成
resource "google_sql_database" "app_db" {
  name     = "auto_remediation"
  instance = google_sql_database_instance.postgres.name
}

# データベースユーザー
resource "google_sql_user" "app_user" {
  name     = "app_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# VPC ネットワーク
resource "google_compute_network" "vpc" {
  name                    = "auto-remediation-vpc-${var.environment}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "auto-remediation-subnet-${var.environment}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# Secret Manager - 環境変数
resource "google_secret_manager_secret" "env_vars" {
  secret_id = "auto-remediation-env-${var.environment}"

  replication {
    automatic = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "env_vars" {
  secret = google_secret_manager_secret.env_vars.id

  secret_data = jsonencode({
    DATABASE_URL = "postgresql://app_user:${random_password.db_password.result}@${google_sql_database_instance.postgres.connection_name}/auto_remediation"
    GITHUB_ACCESS_TOKEN = var.github_token
    SLACK_BOT_TOKEN = var.slack_bot_token
    FIREBASE_CONFIG = var.firebase_config
    GCP_PROJECT_ID = var.project_id
    ENVIRONMENT = var.environment
    FRONTEND_URL = "https://${google_cloud_run_service.frontend.status[0].url}"
  })
}

# Secret Manager - GitHub Token
resource "google_secret_manager_secret" "github_token" {
  secret_id = "github-token-${var.environment}"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "github_token" {
  secret = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
}

# Secret Manager - Slack Token
resource "google_secret_manager_secret" "slack_token" {
  secret_id = "slack-bot-token-${var.environment}"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "slack_token" {
  secret = google_secret_manager_secret.slack_token.id
  secret_data = var.slack_bot_token
}

# Cloud Run - Backend
resource "google_cloud_run_service" "backend" {
  name     = "auto-remediation-backend-${var.environment}"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/auto-remediation-backend:latest"

        ports {
          container_port = 8000
        }

        resources {
          limits = {
            cpu    = "2000m"
            memory = "2Gi"
          }
        }

        env {
          name = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.env_vars.secret_id
              key  = "DATABASE_URL"
            }
          }
        }
      }

      service_account_name = google_service_account.backend.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "10"
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.postgres.connection_name
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.apis]
}

# Cloud Run - Frontend
resource "google_cloud_run_service" "frontend" {
  name     = "auto-remediation-frontend-${var.environment}"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/auto-remediation-frontend:latest"

        ports {
          container_port = 3000
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "1Gi"
          }
        }

        env {
          name = "VITE_API_BASE_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "5"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.apis]
}

# IAM - Service Account
resource "google_service_account" "backend" {
  account_id   = "auto-remediation-backend-${var.environment}"
  display_name = "Auto Remediation Backend Service Account"
}

# IAM - Backend Service Account権限
resource "google_project_iam_member" "backend_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Run IAM - パブリックアクセス許可
resource "google_cloud_run_service_iam_member" "backend_public" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Scheduler - 定期タスク
resource "google_cloud_scheduler_job" "audit_cleanup" {
  name             = "audit-log-cleanup-${var.environment}"
  description      = "Daily audit log cleanup"
  schedule         = "0 2 * * *"
  time_zone        = "UTC"
  attempt_deadline = "300s"

  retry_config {
    retry_count = 3
  }

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.backend.status[0].url}/api/v1/admin/cleanup-logs"

    oidc_token {
      service_account_email = google_service_account.backend.email
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "expired_approvals" {
  name             = "expired-approvals-check-${var.environment}"
  description      = "Check for expired approvals every 10 minutes"
  schedule         = "*/10 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "60s"

  retry_config {
    retry_count = 2
  }

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.backend.status[0].url}/api/v1/admin/check-expired-approvals"

    oidc_token {
      service_account_email = google_service_account.backend.email
    }
  }

  depends_on = [google_project_service.apis]
}

# Cloud Monitoring - アラート
resource "google_monitoring_alert_policy" "error_rate" {
  display_name = "High Error Rate - Auto Remediation ${title(var.environment)}"
  combiner     = "OR"

  conditions {
    display_name = "Error rate too high"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.label.service_name=\"auto-remediation-backend-${var.environment}\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 10

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.name
  ]
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notification - Auto Remediation"
  type         = "email"

  labels = {
    email_address = "admin@example.com"  # 実際のメールアドレスに変更
  }
}

# Outputs
output "backend_url" {
  value = google_cloud_run_service.backend.status[0].url
}

output "frontend_url" {
  value = google_cloud_run_service.frontend.status[0].url
}

output "database_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}
