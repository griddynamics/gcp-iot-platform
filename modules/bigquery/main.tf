resource "google_bigquery_table" "iot_events" {
  deletion_protection = false
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = "iot_events"
  schema              = file("${var.path_to_schema}/iot_events.json")
}

resource "google_bigquery_table" "iot_events_analyzed" {
  deletion_protection = false
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = "iot_events_analyzed"
  schema              = file("${var.path_to_schema}/iot_events_analyzed.json")
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id = "${var.resource_prefix}_iot"
  location   = var.region
  project    = var.project_id
  delete_contents_on_destroy = true
}


resource "google_bigquery_job" "load_data_from_gcs" {
  job_id   = "${var.resource_prefix}-${formatdate("DD-MM-YY'T'hh-mm-ss", timestamp())}"
  project  = var.project_id
  location = var.region

  load {
    source_uris = [
      "${var.data_bucket}/data/device_history_data.csv"
    ]

    destination_table {
      project_id = google_bigquery_table.iot_events.project
      dataset_id = google_bigquery_table.iot_events.dataset_id
      table_id   = google_bigquery_table.iot_events.table_id
    }

    skip_leading_rows = 1
    schema_update_options = ["ALLOW_FIELD_RELAXATION", "ALLOW_FIELD_ADDITION"]

    write_disposition = "WRITE_APPEND"
    autodetect = true
  }
}
