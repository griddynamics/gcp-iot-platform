import logging
import os

import google.cloud.logging
from google.cloud.dataflow import TemplatesServiceClient, CreateJobFromTemplateRequest


def create_job_from_template(unused_request):
    log_client = google.cloud.logging.Client()
    log_client.setup_logging()
    client = TemplatesServiceClient()
    request = CreateJobFromTemplateRequest(
        project_id=os.environ.get('project_id'),
        job_name=os.environ.get('job_name'),
        gcs_path=os.environ.get('template_gcs_path'),
        parameters={
            'input_subscription': os.environ.get('input_subscription'),
            'window_size': os.environ.get('window_size'),
            'output_path': os.environ.get('output_path'),
            'num_shards': os.environ.get('num_shards'),
        },
    )
    response = client.create_job_from_template(request=request)
    logging.info(response)
    return(str(response))
