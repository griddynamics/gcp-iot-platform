variable "resource_prefix" {
  type = string
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "zone" {
  type = string
}

variable "registry_name" {
  type = string
}

variable "device_name" {
  type = string
}

variable "image_family" {
  description = "The family for the compute image. This module has assumptions about the OS being Ubuntu."
  default     = "debian-10"
}

variable "image_project" {
  description = "The project of the compute image owner."
  default     = "debian-cloud"
}

variable "path_module" {
  type = string
}

variable "subnetwork_name" {
  description = "The name of the existing subnetwork where the bastion will be created."
}

variable "network_name" {
  description = "The name of the network where the bastion SSH firewall rule will be created. This network is the parent of $subnetwork"
}

variable "bucket" {
  type = string
}

variable "name_client" {
  type = string
}
