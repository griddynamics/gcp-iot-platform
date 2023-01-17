output "registry_name" {
  value = google_cloudiot_registry.iot_registry.name
}

output "device_name" {
  value = google_cloudiot_device.iot_device.name
}
