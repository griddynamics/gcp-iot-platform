variable "region" {
  description = "The region where the bastion should be provisioned. This is a required input for the google_compute_region_instance_group_manager Terraform resource, and is not inherited from the provider."
}

variable "project_id" {}

variable "resource_prefix" {}
