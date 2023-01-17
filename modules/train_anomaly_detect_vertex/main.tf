resource "google_service_account" detect_anomaly_trainer_vertex {
  account_id   = "${var.resource_prefix}-model-training-vertex"
  display_name = "Service account for function trainer detect anomaly vertex"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.detect_anomaly_trainer_vertex.email}"
}

resource "google_project_iam_member" "artifactregistry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.detect_anomaly_trainer_vertex.email}"
}

resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.detect_anomaly_trainer_vertex.email}"
}

resource "google_project_iam_member" "cloud_build" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.detect_anomaly_trainer_vertex.email}"
}

resource "google_project_iam_member" "sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.detect_anomaly_trainer_vertex.email}"
}

resource "google_cloudfunctions2_function" train_detect_anomaly_vertex {
  depends_on = [google_project_iam_member.sa_user]
  name       = "${var.resource_prefix}-detect-anomaly-trainer-vertex"
  location   = var.region
  build_config {
    runtime = "python39"
    entry_point = "main"
    source {
      storage_source {
        bucket = var.bucket
        object = "functions/startVertexAITrainingPipeline.zip"
      }
    }
  }
  service_config {
    max_instance_count  = 1
    available_memory    = "512M"
    timeout_seconds     = 2000
    ingress_settings = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
    service_account_email = google_service_account.detect_anomaly_trainer_vertex.email
    environment_variables = {
      predictor_image  = "${var.docker_registry}/gd-vai-ad-tma/vai-ad-tma:${var.image_tag}"
      service_account  = google_service_account.detect_anomaly_trainer_vertex.email
      project_id       = var.project_id
      bucket_name      = var.bucket
      training_package = "anomaly-detection/dist/ts-anomaly-detection-trainer-0.1.1.tar.gz"
      data_location    = "data/export_bq"
      pipeline_root    = "AnomalyDetectionPipelineRoot"
      repository       = "${var.docker_registry}/gd-vertexai-anomaly-detector"
      region           = var.region
      resource_prefix  = var.resource_prefix
      endpoint_name    = var.endpoint_name
      table_id         = var.table_id
      dataset          = var.dataset_id
    }
  }
}

resource "null_resource" "call_trainer_anomaly_detector" {
  depends_on = [google_cloudfunctions2_function.train_detect_anomaly_vertex]
  triggers = {
    region        = var.region
    endpoint_name = var.endpoint_name
    path_module   = "${var.path_module}/clearendpoint.sh"
  }
  provisioner "local-exec" {
    command = "curl -m 2010 -X POST $(gcloud functions describe ${google_cloudfunctions2_function.train_detect_anomaly_vertex.name} --gen2 --region ${var.region} --format='value(serviceConfig.uri)') -H 'Authorization: bearer '$(gcloud auth print-identity-token)''"
  }
  provisioner "local-exec" {
    when    = destroy
    command = "${self.triggers.path_module} ${self.triggers.region} ${self.triggers.endpoint_name}"
  }
}
