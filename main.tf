terraform {
  backend "gcs" {
    bucket  = "adp-tst-terraform-state"
    prefix  = "aeaiot"
  }
}

module "iot" {
  source                    = "git@github.com:griddynamics/gcp-iot-platform.git//platform/"
  image_tag                 = var.image_tag
  resource_prefix           = var.resource_prefix
  region                    = var.region
  zone                      = var.zone
  project_id                = var.project_id
}
