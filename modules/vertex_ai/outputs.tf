output "name" {
  value = google_vertex_ai_dataset.ai-dataset.name
  description = "The google_sql_database_instance name"
}

output "create_time" {
  value = google_vertex_ai_dataset.ai-dataset.create_time
  description = "Creation time of VERTEX_AI dataset"
}
