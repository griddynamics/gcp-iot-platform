output "network_name" {
  value       = module.vpc.network
  description = "The name of the VPC being created"
}

output "subnets_names" {
  value       = module.vpc.subnet
  description = "The name of the subnet being created"
}
