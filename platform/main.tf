module "vpc" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/vpc"
  project_id      = var.project_id
  resource_prefix = var.resource_prefix
  region          = var.region
}

module "vertex_ai" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/vertex_ai"
  resource_prefix = var.resource_prefix
  region          = var.region
  project_id      = var.project_id
}

module "pub_sub_iot" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/pub_sub"
  resource_prefix = var.resource_prefix
}

module "key_generation_iot" {
  source      = "git@github.com:griddynamics/gcp-iot-platform.git//modules/tls_private_key"
  algorithm   = "RSA"
  rsa_bits    = 2048
  path_module = "${path.module}/iot"
}

module "iot_core" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/iot_core"
  depends_on      = [module.pub_sub_iot, module.key_generation_iot]
  resource_prefix = var.resource_prefix
  topic_metrics   = module.pub_sub_iot[0].pub_sub_topic_metrics_id
  topic_state     = module.pub_sub_iot[0].pub_sub_topic_state_id
  public_key      = module.key_generation_iot[0].public_key
  region          = var.region
  path_module     = "${path.module}/iot"
}

resource "google_storage_bucket" "iot_bucket" {
  name          = "${var.resource_prefix}-iot-bucket"
  location      = var.region
  force_destroy = true
  labels = {
    project = var.resource_prefix
  }
}

resource "null_resource" "iot_copy" {
  depends_on = [google_storage_bucket.iot_bucket]
  provisioner "local-exec" {
    command = "gsutil cp -r ${path.module}/iot/data ${google_storage_bucket.iot_bucket[count.index].url}"
  }
  provisioner "local-exec" {
    command = "gsutil cp -r ${path.module}/functions ${google_storage_bucket.iot_bucket[count.index].url}"
  }
  provisioner "local-exec" {
    command = "gsutil cp -r ${path.module}/vertex-ai/anomaly-detection ${google_storage_bucket.iot_bucket[count.index].url}"
  }
}

module "bigquery" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/bigquery"
  depends_on      = [null_resource.iot_copy]
  resource_prefix = var.resource_prefix
  project_id      = var.project_id
  region          = var.region
  path_to_schema  = "${path.module}/iot/schema"
  data_bucket     = google_storage_bucket.iot_bucket[count.index].url
}

module "load_iot_events_to_bq" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/iot_events_to_bq"
  depends_on      = [module.bigquery]
  resource_prefix = var.resource_prefix
  project_id      = var.project_id
  region          = var.region
  table_id        = module.bigquery[0].id_table_iot_events
  dataset_id      = module.bigquery[0].dataset_id
  topic_metrics   = module.pub_sub_iot[0].pub_sub_topic_metrics_id
  bucket          = google_storage_bucket.iot_bucket[count.index].name
}

module "anomaly_detector" {
  source            = "git@github.com:griddynamics/gcp-iot-platform.git//modules/anomaly_detector"
  depends_on        = [module.load_iot_events_to_bq]
  resource_prefix   = var.resource_prefix
  project_id        = var.project_id
  region            = var.region
  bucket            = google_storage_bucket.iot_bucket[count.index].name
  topic_metrics     = module.pub_sub_iot[0].pub_sub_topic_metrics_id
  dataset_id        = module.bigquery[0].dataset_id
  table_id_analyzed = module.bigquery[0].id_table_iot_events_analyzed
  registry_id       = module.iot_core[0].registry_id
}

module "anomaly_detector_vertex" {
  source            = "git@github.com:griddynamics/gcp-iot-platform.git//modules/anomaly_detector_vertex"
  depends_on        = [module.load_iot_events_to_bq]
  resource_prefix   = var.resource_prefix
  project_id        = var.project_id
  region            = var.region
  bucket            = google_storage_bucket.iot_bucket[count.index].name
  dataset_id        = module.bigquery[0].dataset_id
  topic_metrics     = module.pub_sub_iot[0].pub_sub_topic_metrics_id
  table_id_analyzed = module.bigquery[0].id_table_iot_events_analyzed
  table_id          = module.bigquery[0].id_table_iot_events
  registry_id       = module.iot_core[0].registry_id
}

module "train_anomaly_detection" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/train_anomaly_detection"
  depends_on      = [module.load_iot_events_to_bq]
  resource_prefix = var.resource_prefix
  project_id      = var.project_id
  region          = var.region
  table_id        = module.bigquery[0].id_table_iot_events
  dataset_id      = module.bigquery[0].dataset_id
  bucket          = google_storage_bucket.iot_bucket[count.index].name
}

module "train_detect_anomaly_vertex" {
  source          = "git@github.com:griddynamics/gcp-iot-platform.git//modules/train_anomaly_detect_vertex"
  depends_on      = [module.pub_sub_iot]
  resource_prefix = var.resource_prefix
  project_id      = var.project_id
  region          = var.region
  bucket          = google_storage_bucket.iot_bucket[count.index].name
  docker_registry = var.docker_registry
  image_tag       = var.image_tag
  endpoint_name   = "${var.resource_prefix}-anomaly-kfp"
  table_id        = module.bigquery[0].id_table_iot_events
  dataset_id      = module.bigquery[0].dataset_id
  path_module     = "${path.module}/iot"
}

module "dataflow_job" {
  source            = "git@github.com:griddynamics/gcp-iot-platform.git//modules/function_dataflow_job"
  depends_on        = [module.train_anomaly_detection]
  resource_prefix   = var.resource_prefix
  project_id        = var.project_id
  region            = var.region
  bucket_name       = google_storage_bucket.iot_bucket[count.index].name
  bucket_url        = google_storage_bucket.iot_bucket[count.index].url
  subscription_name = module.pub_sub_iot[0].subscription_name
  subscription_id   = module.pub_sub_iot[0].subscription_id
  path_module       = "${path.module}/dataflow/pubsubGcs"
}

module "mqtt_client" {
  source           = "git@github.com:griddynamics/gcp-iot-platform.git//modules/mqtt_client"
  depends_on       = [module.dataflow_job]
  resource_prefix  = var.resource_prefix
  project_id       = var.project_id
  region           = var.region
  zone             = var.zone
  registry_name    = module.iot_core[0].registry_name
  device_name      = module.iot_core[0].device_name
  bucket           = google_storage_bucket.iot_bucket[count.index].name
  subnetwork_name  = module.vpc.subnet_name
  network_name     = module.vpc.vpc_name
  path_module      = "${path.module}/iot"
  name_client      = "${var.resource_prefix}-mqtt-client"
}
