output "network_name" {
  value       = module.iot.network_name
  description = "The name of the VPC being created"
}

output "subnets_names" {
  value       = module.iot.subnets_names
  description = "The name of the subnet being created"
}
