resource "google_service_account" train_anomaly_detection {
  account_id   = "${var.resource_prefix}-model-training"
  display_name = "Service account for function anomaly detector trainer"
}

resource "google_project_iam_member" "bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.train_anomaly_detection.email}"
}

resource "google_cloudfunctions_function" train_anomaly_detection {
  depends_on            = [google_project_iam_member.bigquery_admin]
  name                  = "${var.resource_prefix}-train-anomaly-detection"
  region                = var.region
  runtime               = "python310"
  available_memory_mb   = 256
  source_archive_bucket = var.bucket
  source_archive_object = "functions/trainDetector.zip"
  entry_point           = "main"
  service_account_email = google_service_account.train_anomaly_detection.email
  trigger_http          = true
  environment_variables = {
    table_id     = var.table_id
    project_id   = var.project_id
    dataset      = var.dataset_id
    model_prefix = "arima_det_model_"
  }
  ingress_settings = "ALLOW_ALL"
}

resource "null_resource" "call_training_function" {
  depends_on = [google_cloudfunctions_function.train_anomaly_detection]
  provisioner "local-exec" {
    command = "gcloud functions call ${google_cloudfunctions_function.train_anomaly_detection.name} --region ${var.region}"
  }
}

resource "google_cloud_scheduler_job" "job" {
  depends_on = [google_cloudfunctions_function.train_anomaly_detection]
  name             = google_cloudfunctions_function.train_anomaly_detection.name
  schedule         = "*/30 * * * *"
  attempt_deadline = "180s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.train_anomaly_detection.https_trigger_url

    oidc_token {
      service_account_email = google_service_account.train_anomaly_detection.email
    }
  }
}
