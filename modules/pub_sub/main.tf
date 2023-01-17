resource "google_pubsub_topic" "pub_sub_topic_metrics" {
  name = "${var.resource_prefix}-iot-metrics"
}

resource "google_pubsub_topic" "pub_sub_topic_state" {
  name = "${var.resource_prefix}-iot-state"
}

resource "google_pubsub_subscription" "pub_sub_subscription" {
  name  = "${var.resource_prefix}-iot-metrics-subscription"
  topic = google_pubsub_topic.pub_sub_topic_metrics.name
}
