#User-defined variables
variable "project_id" {
  description = "A globally unique identifier for your project"
  default     = "YOUR_PROJECT"
}

variable "resource_prefix" {
  description     = "Platform deployment identifier. This variable is part of GCS state bucket name, so it should follow GCS naming restrictions. Length from 3 to 11 symbols. Bucket names can consist only of lowercase letters, numbers, dots (.), and hyphens (-). Bucket names must begin and end with a letter or number."
  default         = "adp"
  validation {
    condition     = length(var.resource_prefix) > 2 && length(var.resource_prefix) < 12
    error_message = "ResourcePrefix value must be a length Length from 2 to 11 symbols."
  }
}

variable "region" {
  description = "Enter region for platform"
  default     = "us-central1"
}

variable "zone" {
  description = "Main zone in region"
  default = "us-central1-a"
}

variable "docker_registry" {
  description = "Docker registry from the Google Artifact Registry"
  default = "YOUR_REGISTRY"
  type = string
}

variable "image_tag" {
  description = "Tags of images from the Google Artifact Registry"
  default     = "0.10.0"
  type        = string
}
