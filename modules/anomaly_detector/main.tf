resource "google_service_account" anomaly_detector {
  account_id   = "${var.resource_prefix}-anomaly-detector"
  display_name = "Service account for function anomaly detector"
}

resource "google_project_iam_member" "bigquery_dataeditor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.anomaly_detector.email}"
}

resource "google_cloudfunctions_function" anomaly_detector {
  depends_on            = [google_project_iam_member.bigquery_dataeditor]
  name                  = "${var.resource_prefix}-anomaly-detector"
  region                = var.region
  runtime               = "python310"
  available_memory_mb   = 256
  source_archive_bucket = var.bucket
  source_archive_object = "functions/analyzeIoTPopulateCallback.zip"
  entry_point           = "main"
  service_account_email = google_service_account.anomaly_detector.email
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = var.topic_metrics
  }
  environment_variables = {
    model_prefix      = "arima_det_model_"
    dataset           = var.dataset_id
    project_id        = var.project_id
    destination_table = var.table_id_analyzed
    cloud_region      = var.region
    registry_id       = var.registry_id
  }
  ingress_settings      = "ALLOW_ALL"
}
