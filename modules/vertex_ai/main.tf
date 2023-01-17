resource "google_vertex_ai_dataset" "ai-dataset" {
  display_name          = "${var.resource_prefix}-dataset-vertex-ai"
  metadata_schema_uri   = "gs://google-cloud-aiplatform/schema/dataset/metadata/image_1.0.0.yaml"
  region                = var.region
  project               = var.project_id
}
