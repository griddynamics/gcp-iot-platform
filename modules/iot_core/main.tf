resource "google_cloudiot_registry" "iot_registry" {
  name     = "${var.resource_prefix}-cloudiot-device-registry"

  event_notification_configs {
    pubsub_topic_name = var.pubsub_topic
  }
  http_config = {
    http_enabled_state = "HTTP_DISABLED"
  }
}

resource "google_cloudiot_device" "iot_device" {
  name     = "${var.resource_prefix}-cloudiot-device"
  registry = google_cloudiot_registry.iot_registry.id
}
