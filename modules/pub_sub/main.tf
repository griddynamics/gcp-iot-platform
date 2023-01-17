resource "google_pubsub_topic" "pub_sub_topic_empty" {
  name = "${var.resource_prefix}-iot-metrics"
}

resource "google_pubsub_subscription" "pub_sub" {
  name  = "${var.resource_prefix}-subscription"
  topic = google_pubsub_topic.pub_sub_topic_empty.name
}
