locals {
  network_name                   = "${var.resource_prefix}-vpc"
  subnet_name                    = "${google_compute_network.vpc.name}-subnet"
  ip_cidr_range_subnet           = "10.10.0.0/16"
  cluster_master_ip_cidr_range   = "10.100.100.0/28"
  cluster_pods_ip_cidr_range     = "10.101.0.0/16"
  cluster_services_ip_cidr_range = "10.102.0.0/16"
}

resource "google_compute_network" "vpc" {
  name                            = local.network_name
  auto_create_subnetworks         = false
  routing_mode                    = "GLOBAL"
  delete_default_routes_on_create = true
  project                         = var.project_id
}

resource "google_compute_subnetwork" "subnet" {
  name                     = local.subnet_name
  ip_cidr_range            = local.ip_cidr_range_subnet
  region                   = var.region
  network                  = google_compute_network.vpc.name
  private_ip_google_access = true
  project                  = var.project_id
}

resource "google_compute_route" "egress_internet" {
  name             = "${var.resource_prefix}-egress-internet"
  dest_range       = "0.0.0.0/0"
  network          = google_compute_network.vpc.name
  next_hop_gateway = "default-internet-gateway"
  project          = var.project_id
}

resource "google_compute_router" "router" {
  name    = "${local.network_name}-router"
  region  = google_compute_subnetwork.subnet.region
  network = google_compute_network.vpc.name
  project = var.project_id
}

resource "google_compute_router_nat" "nat_router" {
  name                               = "${google_compute_subnetwork.subnet.name}-nat-router"
  router                             = google_compute_router.router.name
  region                             = google_compute_router.router.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  project                            = var.project_id

  subnetwork {
    name                    = google_compute_subnetwork.subnet.name
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
