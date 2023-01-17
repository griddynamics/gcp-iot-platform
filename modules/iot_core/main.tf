resource "google_cloudiot_registry" "iot_registry" {
  name       = "${var.resource_prefix}-cloudiot-device-registry"
  region     = var.region

  event_notification_configs {
    pubsub_topic_name = var.topic_metrics
  }
  state_notification_config = {
    pubsub_topic_name = var.topic_state
  }

  http_config = {
    http_enabled_state = "HTTP_DISABLED"
  }
}

resource "google_cloudiot_device" "iot_device" {
  name       = "${var.resource_prefix}-cloudiot-device"
  registry   = google_cloudiot_registry.iot_registry.id
  credentials {
    public_key {
      format = "RSA_PEM"
      key    = var.public_key
    }
  }
}

resource "null_resource" "prepare_for_device" {
  depends_on = [google_cloudiot_device.iot_device]
  provisioner "local-exec" {
    command = "gcloud iot devices configs update --format=text --config-file=${var.path_module}/mqtt_client/config.json --device=${google_cloudiot_device.iot_device.name} --registry=${google_cloudiot_registry.iot_registry.name} --region=${var.region}"
  }
}
