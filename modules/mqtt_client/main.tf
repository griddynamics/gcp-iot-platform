data "template_file" "startup_script" {
  template = <<-EOF
  sudo apt-get remove -y --purge man-db
  sudo apt-get install python3-pip --yes
  pip3 install --upgrade pip
  pip3 install --upgrade setuptools
  pip3 install --no-cache-dir  --force-reinstall -Iv grpcio
  pip3 install paho-mqtt==1.6.1
  pip3 install PyJWT==2.4.0
  pip3 install cryptography==37.0.4
  pip3 install -U google-cloud-logging==3.2.1
  pip3 install -U google-cloud-storage==2.4.0
  pip3 install -U google-cloud-compute==1.4.0
  EOF
}

data "template_file" "script_mqtt_client" {
  template   = file("${var.path_module}/mqtt_client/run_mqtt_client.py")
  vars = {
    algorithm   = "RS256"
    device_id   = var.device_name
    region      = var.region
    project_id  = var.project_id
    zone        = var.zone
    mqtt_client = google_compute_instance.mqtt_client.name
    registry_id = var.registry_name
    bucket      = var.bucket
  }
}

resource "google_service_account" "mqtt_client_sa" {
  account_id   = "${var.resource_prefix}-mqtt-client-sa"
  display_name = "Service Account for mqtt client"
}

resource "google_project_iam_member" "pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.mqtt_client_sa.email}"
}

resource "google_project_iam_member" "pubsub_viewer" {
  project = var.project_id
  role    = "roles/pubsub.viewer"
  member  = "serviceAccount:${google_service_account.mqtt_client_sa.email}"
}

resource "google_project_iam_member" "pubsub_editor" {
  project = var.project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.mqtt_client_sa.email}"
}

resource "google_project_iam_member" "instance_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin"
  member  = "serviceAccount:${google_service_account.mqtt_client_sa.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.mqtt_client_sa.email}"
}

resource "google_project_iam_member" "storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.mqtt_client_sa.email}"
}

resource "google_compute_instance" "mqtt_client" {
  depends_on = [google_project_iam_member.instance_admin]
  machine_type = "e2-small"
  name         = var.name_client
  zone         = var.zone
  tags         = [var.name_client, "terraform-managed"]
  boot_disk {
    initialize_params {
      image = "${var.image_project}/${var.image_family}"
    }
    auto_delete  = true
  }
  network_interface {
    subnetwork_project = var.project_id
    subnetwork         = var.subnetwork_name
  }
  metadata_startup_script = data.template_file.startup_script.rendered
  service_account {
    email = google_service_account.mqtt_client_sa.email
    scopes = ["cloud-platform", "pubsub", "userinfo-email", "compute-rw", "storage-full"]
  }
}

resource "google_compute_firewall" "mqtt_client" {
  name          = "${google_compute_instance.mqtt_client.name}-firewall"
  project       = var.project_id
  network       = var.network_name
  source_ranges = ["35.235.240.0/20"]
  target_tags   = [var.name_client]
  direction     = "INGRESS"
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "local_file" "prepare_for_mqtt_client" {
  depends_on = [google_compute_firewall.mqtt_client, data.template_file.script_mqtt_client]
  content = data.template_file.script_mqtt_client.rendered
  filename = "${var.path_module}/iot/mqtt_client/run_mqtt_client.py"
  provisioner "local-exec" {
    command = "sleep 400"
  }
  provisioner "local-exec" {
    command = "gcloud compute scp ${var.path_module}/template/*.pem ${var.name_client}:~/ --project ${var.project_id} --zone ${var.zone}"
  }
  provisioner "local-exec" {
    command = "gcloud compute scp ${local_file.prepare_for_mqtt_client.filename} ${var.path_module}/mqtt_client/client.py ${var.name_client}:~/ --project ${var.project_id} --zone ${var.zone}"
  }
  provisioner "local-exec" {
    command = "gcloud compute ssh ${var.name_client} --project ${var.project_id} --zone ${var.zone} --ssh-flag='-T' -- 'curl https://pki.goog/roots.pem >> ~/root.pem'"
  }
#  provisioner "local-exec" {
#    command = "gcloud compute ssh ${var.name_client} --project ${var.project_id} --zone ${var.zone} --ssh-flag='-T' -- 'python3 run_mqtt_client.py'"
#  }
}
