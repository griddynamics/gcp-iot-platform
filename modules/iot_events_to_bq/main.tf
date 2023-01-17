resource "google_service_account" iot_events {
  account_id   = "${var.resource_prefix}-iot-events"
  display_name = "Service account for function load iot events to bq"
}

resource "google_project_iam_member" "bigquery_dataeditor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.iot_events.email}"
}

resource "google_cloudfunctions_function" iot_events_to_bq {
  depends_on            = [google_project_iam_member.bigquery_dataeditor]
  name                  = "${var.resource_prefix}-iot-events-to-bq"
  region                = var.region
  runtime               = "python310"
  available_memory_mb   = 256
  source_archive_bucket = var.bucket
  source_archive_object = "functions/iotBigQueryEvents.zip"
  entry_point           = "iot_events_to_bq"
  service_account_email = google_service_account.iot_events.email
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = var.topic_metrics
  }
  environment_variables = {
    table_id     = var.table_id
    project_id   = var.project_id
    dataset      = var.dataset_id
    date_point   = "2011-08-03T23:25:01"
    interval_sec = 60
    ts_format    = "%Y-%m-%dT%H:%M:%S"
  }
  ingress_settings      = "ALLOW_ALL"
}
