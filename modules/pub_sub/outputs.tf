output "pub_sub_topic_metrics_name" {
  value = google_pubsub_topic.pub_sub_topic_metrics.name
}

output "pub_sub_topic_state_name" {
  value = google_pubsub_topic.pub_sub_topic_state.name
}

output "pub_sub_topic_metrics_id" {
  value = google_pubsub_topic.pub_sub_topic_metrics.id
}

output "pub_sub_topic_state_id" {
  value = google_pubsub_topic.pub_sub_topic_state.id
}

output "subscription_name" {
  value = google_pubsub_subscription.pub_sub_subscription.name
}

output "subscription_id" {
  value = google_pubsub_subscription.pub_sub_subscription.id
}
