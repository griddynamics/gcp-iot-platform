terraform {
  required_version = ">=0.12.6"
#
  required_providers {
    google = {
      version = ">= 3.45.0"
    }
    null = {
      version = "~> 2.1"
    }
  }
}
