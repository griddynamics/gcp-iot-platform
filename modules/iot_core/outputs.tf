output "registry_name" {
  value = google_cloudiot_registry.iot_registry.name
}

output "registry_id" {
  value = google_cloudiot_registry.iot_registry.id
}

output "device_name" {
  value = google_cloudiot_device.iot_device.name
}

output "device_id" {
  value = google_cloudiot_device.iot_device.id
}
