resource "null_resource" "template_in_gcs" {
  provisioner "local-exec" {
    command = "chmod +x ${var.path_module}/dataflow_classic_template.sh && ./${var.path_module}/dataflow_classic_template.sh ${var.path_module} ${var.project_id} ${var.bucket_url} ${var.region} ${var.subscription_id} ${var.bucket_name} ${google_service_account.dataflow_job.email}"
  }
}

resource "google_service_account" dataflow_job {
  account_id   = "${var.resource_prefix}-dataflow-job"
  display_name = "Service account for function dataflow job"
}

resource "google_project_iam_member" "dataflow_developer" {
  member  = "serviceAccount:${google_service_account.dataflow_job.email}"
  project = var.project_id
  role    = "roles/dataflow.developer"
}

resource "google_project_iam_member" "dataflow_worker" {
  member  = "serviceAccount:${google_service_account.dataflow_job.email}"
  project = var.project_id
  role    = "roles/dataflow.worker"
}

resource "google_project_iam_member" "storage_viewer" {
  member  = "serviceAccount:${google_service_account.dataflow_job.email}"
  project = var.project_id
  role    = "roles/storage.objectViewer"
}

resource "google_project_iam_member" "pub_sub_editor" {
  member  = "serviceAccount:${google_service_account.dataflow_job.email}"
  project = var.project_id
  role    = "roles/pubsub.editor"
}

resource "google_project_iam_member" "account_user" {
  member  = "serviceAccount:${google_service_account.dataflow_job.email}"
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
}

resource "google_cloudfunctions_function" dataflow_job {
  depends_on            = [google_project_iam_member.account_user]
  name                  = "${var.resource_prefix}-dataflow-job"
  region                = var.region
  runtime               = "python310"
  available_memory_mb   = 128
  source_archive_bucket = var.bucket_name
  source_archive_object = "functions/pubsubGcsDataflowJob.zip"
  entry_point           = "create_job_from_template"
  service_account_email = google_service_account.dataflow_job.email
  trigger_http          = true
  environment_variables = {
    project_id         = var.project_id
    job_name           = "${var.resource_prefix}-iot-pubsub-gcs"
    template_gcs_path  = "${var.bucket_url}/templates/iot-pubsub-gcs"
    input_subscription = var.subscription_name
    window_size        = "1.0"
    output_path        = "${var.bucket_url}/output"
    num_shards         = "1"
  }
  ingress_settings = "ALLOW_ALL"
}
