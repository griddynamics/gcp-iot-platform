#User-defined variables
variable "project_id" {
  description = "The project ID to host the network in"
}

variable "resource_prefix" {
  description = "Base Platform deployment identifier. This variable is part of Google Storage, Service Account etc names, so it should follow names restrictions these resources. Length from 3 to 11 symbols. Names can consist only of lowercase letters, numbers, dots (.), hyphens (-) and must begin and end with a letter or number."
  validation {
    condition     = length(var.resource_prefix) > 2 && length(var.resource_prefix) < 12
    error_message = "ResourcePrefix value must be a length Length from 3 to 11 symbols."
  }
}

variable "region" {
  description = "Enter region for platform"
  #  default = "us-central1"
}

variable "zone" {
  description = "Main zone in region"
  default     = "us-central1-a"
}

#Platform Parameters
variable "docker_registry" {
  type = string
}

variable "image_tag" {
  type = string
}
