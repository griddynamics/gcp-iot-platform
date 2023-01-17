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
* Artifact Registry API
* IAM Service Account Credentials API
* Vertex AI API
* Google Cloud IoT API
* Dataflow API
* BigQuery API
* BigQuery Storage API
* Cloud Build API
* Cloud Pub/Sub API
* Cloud Functions API
* Cloud Run Admin API
* Serverless VPC Access API
* Compute Engine API
* Cloud Monitoring API
* Cloud Logging API

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
For more information check this link to terraform official documentation: 
https://www.terraform.io/language/settings/backends/gcs

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

* [Grid Dynamics blog post](#)