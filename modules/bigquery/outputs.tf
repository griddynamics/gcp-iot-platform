output "uri_dataset" {
  value = google_bigquery_dataset.dataset.self_link
  description = "The URI of the created dataset"
}

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
  description = "Dataset ID"
}

output "uri_table_iot_events" {
  value = google_bigquery_table.iot_events.self_link
  description = "The URI of the iot events table"
}

output "id_table_iot_events" {
  value = google_bigquery_table.iot_events.table_id
  description = "BigQuery iot events table ID"
}

output "uri_table_iot_events_analyzed" {
  value = google_bigquery_table.iot_events_analyzed.self_link
  description = "The URI of the analyzed iot events table"
}

output "id_table_iot_events_analyzed" {
  value = google_bigquery_table.iot_events_analyzed.table_id
  description = "BigQuery analyzed iot events table ID"
}

output "id_job" {
  value = google_bigquery_job.load_data_from_gcs.id
  description = "Job ID"
}
