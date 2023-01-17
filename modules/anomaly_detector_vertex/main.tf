resource "google_service_account" anomaly_detector_vertex {
  account_id   = "${var.resource_prefix}-anomaly-detector-vertex"
  display_name = "Service account for function anomaly detector VertexAI "
}

resource "google_project_iam_member" "bigquery_dataeditor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.anomaly_detector_vertex.email}"
}

resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.anomaly_detector_vertex.email}"
}

resource "google_project_iam_member" "artifactregistry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.anomaly_detector_vertex.email}"
}

resource "google_cloudfunctions_function" anomaly_detector_vertex {
  depends_on            = [google_project_iam_member.artifactregistry_writer]
  name                  = "${var.resource_prefix}-anomaly-detector_vertex"
  region                = var.region
  runtime               = "python39"
  available_memory_mb   = 512
  source_archive_bucket = var.bucket
  source_archive_object = "functions/detectAnomalyVertex.zip"
  entry_point           = "main"
  service_account_email = google_service_account.anomaly_detector_vertex.email
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = var.topic_metrics
  }
  environment_variables = {
    project_id        = var.project_id
    cloud_region      = var.region
    registry_id       = var.registry_id
    dataset           = var.dataset_id
    endpoint_name     = "anomaly-kfp"
    input_size        = 24
    period            = 3600
    table_id          = var.table_id
    destination_table = var.table_id_analyzed
  }
  ingress_settings      = "ALLOW_ALL"
}
