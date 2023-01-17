output "network" {
  value       = google_compute_network.vpc
  description = "The VPC"
}

output "self_link" {
  value       = google_compute_network.vpc.self_link
  description = "The VPC self link"
}

output "vpc_name" {
  value       = google_compute_network.vpc.name
  description = "The VPC Name"
}

output "vpc_id" {
  value       = google_compute_network.vpc.id
  description = "The VPC id"
}

output "subnet" {
  value       = google_compute_subnetwork.subnet
  description = "The subnet link"
}

output "subnet_name" {
  value       = google_compute_subnetwork.subnet.name
  description = "The subnet name"
}

output "subnet_id" {
  value       = google_compute_subnetwork.subnet.id
  description = "The subnet id"
}

output "cluster_master_ip_cidr_range" {
  value       = local.cluster_master_ip_cidr_range
  description = "The CIDR range to use for Kubernetes cluster master"
}

output "cluster_pods_ip_cidr_range" {
  value       = local.cluster_pods_ip_cidr_range
  description = "The CIDR range to use for Kubernetes cluster pods"
}

output "cluster_services_ip_cidr_range" {
  value       = local.cluster_services_ip_cidr_range
  description = "The CIDR range to use for Kubernetes cluster services"
}
