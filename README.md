<!--
Copyright 2022 Grid Dynamics
-->

# IoT platform

This is developed a starter kit for building an IoT platform from scratch in GCP. 
The goal of this accelerator is to provide modular components to address various capabilities such as data collection, deployment to the edge, 
IoT device management, and more, thereby reducing the  time to market for developing IoT platform from scratch

## Table of resources
* VPC
* Cloud Functions
* BigQuery
* Dataflow
* IoT core
* Pub/Sub
* Vertex ai
* VM instance (mqtt client demo)

## Prepare for deploying

Platform deployment is carried out using terraform. 
For deploying the IoT Platform need to activate Google Cloud Platform API Tools, 
adding roles for access to automation deploying, creating bucket for storage state files for terraform.

## API Tools for working with IoT at GCP
Enable this API for working with all part of the platform:
* [Artifact Registry API](https://cloud.google.com/artifact-registry/docs/reference/rest)
* [IAM Service Account Credentials API](https://cloud.google.com/iam/docs/reference/credentials/rest)
* [Vertex AI API](https://cloud.google.com/vertex-ai/docs/reference/rest)
* [Google Cloud IoT API](https://cloud.google.com/iot/docs/reference/cloudiotdevice/rest)
* [Dataflow API](https://cloud.google.com/dataflow/docs/reference/rest)
* [BigQuery API](https://cloud.google.com/bigquery/docs/reference/rest)
* BigQuery Storage API
* [Cloud Build API](https://cloud.google.com/build/docs/api/reference/rest)
* [Cloud Pub/Sub API](https://cloud.google.com/pubsub/docs/reference/rest)
* [Cloud Functions API](https://cloud.google.com/functions/docs/reference/rest)
* [Cloud Run Admin API](https://cloud.google.com/run/docs/reference/rest)
* [Serverless VPC Access API](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access)
* [Compute Engine API](https://cloud.google.com/compute/docs/reference/rest/v1)
* [Cloud Monitoring API](https://cloud.google.com/monitoring/api/v3)
* [Cloud Logging API](https://cloud.google.com/logging/docs/reference/v2/rest)

## Roles for deploy IoT into GCP

Roles list at here:
* Compute Instance Admin (v1)
* Compute Network Admin
* Container Threat Detection Service Agent
* Editor
* IAP-secured Tunnel User
* Storage Object Admin
* Project IAM Admin
* BigQuery Admin

## Create bucket for store terraform state files
The next step you need to create bucket with unically name which will be specified before deployment here:
```smartyconfig
terraform {
 backend "gcs" {
   bucket  = "gd-tst-terraform-state"
   prefix  = "some-prefix-here"
 }
}
```
This is required for storage terraform state files remotely.
For more information check this link to terraform [official documentation](https://www.terraform.io/language/settings/backends/gcs)

## Platform customization
Next step you can start preparing the deployment of the platform with customized configs

1. You need to set up the name of your state bucket to the main.tf file into the ENV repo
```smartyconfig
terraform {
 backend "gcs" {
   bucket  = "gd-tst-terraform-state"
   prefix  = "some-prefix-here"
 }
}
```
2. In the ENV repository on extra.tfvars file you need to customize your build options. 
Also specify your prefix under which the state will be stored on the platform. Description of the variables you can see below. 

## Here in the parameters list, the following parameters are mandatory and must be filled in:
* project_id - A globally unique identifier for your project.
* resource_prefix - Platform deployment identifier. This variable is part of GCS bucket name, so it should follow GCS naming restrictions. Length from 3 to 11 symbols. Bucket names can consist only of lowercase letters, numbers, dots (.), and hyphens (-). Bucket names must begin and end with a letter or number.
* region - Enter region for platform.
* zone - Main zone in region
* image_tag - Tags of images from the Google Artifact Registry.

## Note
Iot Core working only in asia-east1, europe-west1, us-central1. 
For more information check this link to cloud IoT core [official documentation](https://cloud.google.com/iot/docs/requirements#permitted_characters_and_size_requirements)
## Deploy platform
After customizing the platform, you need to start the deployment
```smartyconfig
tf apply -var-file extra.tfvars
```

## Run demo mqtt client
Module "mqtt client"  this is demo device. In order for this device to work with our IoT platform, you need to connect to the mqtt client (vm instance) and run the python script.
```smartyconfig
gcloud compute ssh YOUR-RESOURCE-PREFIX-mqtt-client --project YOUR-PROJECT --zone YOUR-ZONE --ssh-flag='-T' -- 'python3 run_mqtt_client.py'
```

## Related links

* [Grid Dynamics blog post](https://blog.griddynamics.com/building-an-iot-platform-in-gcp-a-starter-kit/)