import datetime
import os
import functions_framework

from google.cloud import aiplatform
from google_cloud_pipeline_components.types import artifact_types
from google_cloud_pipeline_components.v1.custom_job import CustomTrainingJobOp
from google_cloud_pipeline_components.v1.model import ModelUploadOp
from google_cloud_pipeline_components.v1.endpoint import EndpointCreateOp, ModelDeployOp
from kfp.v2 import dsl
from kfp.v2 import compiler
from kfp.v2.components import importer_node

MODEL_DESCRIPTION = "PyTorch based anomaly detector with custom container"
RESOURCE_PREFIX = os.environ.get('resource_prefix', '')
DISPLAY_NAME = f"{RESOURCE_PREFIX}train-upload-deploy-model"

SERVICE_ACCOUNT = os.environ.get("service_account")
PROJECT_ID = os.environ.get("project_id")
BUCKET_NAME = os.environ.get("bucket_name")
ENDPOINT_NAME = os.environ.get("endpoint_name")
TRAINING_PACKAGE = os.environ.get("training_package")
DATA_LOCATION = os.environ.get("data_location")
PIPELINE_ROOT_FOLDER = os.environ.get("pipeline_root")
PREDICTOR_IMAGE = os.environ.get("predictor_image")
REPOSITORY = os.environ.get("repository")
REGION = os.environ.get("region")

NOW = datetime.datetime.now()
BUCKET_URI = f"gs://{BUCKET_NAME}"
PIPELINE_ROOT = f"{BUCKET_URI}/{PIPELINE_ROOT_FOLDER}/"

TRAINER_POOL_SPEC = {
    "machineSpec": {
        "machineType": "n1-standard-4",
        "acceleratorType": "ACCELERATOR_TYPE_UNSPECIFIED",
        "acceleratorNumber": 0,
    },
    "replicaCount": "1",
    "pythonPackageSpec": {
        "executorImageUri": "us-docker.pkg.dev/vertex-ai/training/pytorch-xla.1-11:latest",
        "packageUris": [f"{BUCKET_URI}/{TRAINING_PACKAGE}"],
        "pythonModule": "trainer.task",
        "args": ['-d', f'{BUCKET_URI}/{DATA_LOCATION}', '-l', '0.0001'],
    }
}


@dsl.component(base_image=PREDICTOR_IMAGE)
def predictor_creation_op(model_dir: str, project: str, repository: str, image: dsl.OutputPath(str)):
    import os
    import yaml
    from datetime import datetime
    NOW = datetime.now()
    project_set = os.system(f"gcloud config set project {project}")
    assert project_set == 0, 'Error in setting google cloud project!'
    files_downloaded = os.system(
        f'gsutil cp {model_dir}/model/pytorch_model.bin {model_dir}/model/config.json /home/iot/')
    assert files_downloaded == 0, 'Error in downloading model data!'
    DOCKER_TAG = "torch-ts-anomaly-predictor:" + NOW.strftime('%Y-%m-%d')
    FULL_TAG = repository + '/' + DOCKER_TAG

    with open('/home/iot/cloudbuild.yaml') as f:
        config = yaml.load(f, yaml.SafeLoader)
    # Build substitution
    config['steps'][0]['args'][2] = FULL_TAG
    # Push substitution
    config['steps'][1]['args'][1] = FULL_TAG
    with open('/home/iot/cloudbuild.yaml', 'w') as f:
        config = yaml.dump(config, f, yaml.SafeDumper)

    image_build = os.system(f'gcloud builds submit --config /home/iot/cloudbuild.yaml /home/iot/')
    assert image_build == 0, 'Error in building Predictor image!'
    with open(image, 'w') as f:
        f.write(FULL_TAG)


@dsl.component(base_image='python:3.9',
               packages_to_install=['google-cloud-aiplatform==1.16.1'])
def get_endpoint(project: str, bucket: str, endpoint_name: str, region: str, endpoint_out: dsl.Output[dsl.Artifact]):
    import google.cloud.aiplatform as aip
    aip.init(project=project, staging_bucket=bucket)
    filter = f'display_name="{endpoint_name}"'
    endpoint_info = aip.Endpoint.list(filter=filter)
    if len(endpoint_info) == 0:
        endpoint = aip.Endpoint.create(display_name=endpoint_name, project=project, sync=True)
    else:
        endpoint = aip.Endpoint(endpoint_info[-1].resource_name)
    # Creating VertexEndpoint output as KFP Artifact
    endpoint_out.uri = f"https://{region}-aiplatform.googleapis.com/v1/{endpoint.resource_name}"
    endpoint_out.TYPE_NAME = 'google.VertexEndpoint'
    endpoint_out.metadata['resourceName'] = endpoint.resource_name


@dsl.pipeline(name=DISPLAY_NAME)
def pipeline(project: str, bucket: str, predictor_repository: str, endpoint_name: str, region: str):
    working_dir = PIPELINE_ROOT + f"{dsl.PIPELINE_JOB_ID_PLACEHOLDER}-{NOW.strftime('%Y%m%d')}"
    # Training the model
    custom_job_task = CustomTrainingJobOp(
        project=project,
        base_output_directory=working_dir,
        display_name="anomaly-model-training",
        worker_pool_specs=[TRAINER_POOL_SPEC],
    )
    # Get the endpoint
    endpoint_get_task = get_endpoint(project, bucket, endpoint_name, region)
    # Preparing Vertex AI Predictor compatible Docker image
    predictor = predictor_creation_op(working_dir, project, predictor_repository).after(custom_job_task)
    # Import the prepared image
    model = importer_node.importer(
        artifact_uri=working_dir,
        artifact_class=artifact_types.UnmanagedContainerModel,
        metadata={
            "containerSpec": {
                "imageUri": predictor.outputs['image'],
                "ports": ([{"containerPort": 7080}, ]),
                "predictRoute": "/predictions/anomaly",
                "healthRoute": "/ping"
            },
        },
    )
    # Adding model to VertexAI Model Registry
    upload_model = ModelUploadOp(
        project=project,
        display_name=f"{RESOURCE_PREFIX}anomaly-{NOW.strftime('%Y%m%d')}",
        description=MODEL_DESCRIPTION,
        unmanaged_container_model=model.outputs['artifact'],
    )
    # Deploying
    ModelDeployOp(
        model=upload_model.outputs['model'],
        endpoint=endpoint_get_task.outputs['endpoint_out'],
        deployed_model_display_name=f"{RESOURCE_PREFIX}anomaly-{NOW.strftime('%Y%m%d')}",
        traffic_split={'0': 100},
        dedicated_resources_machine_type='n1-standard-4',
        dedicated_resources_min_replica_count=1,
        dedicated_resources_max_replica_count=1,
    )


@functions_framework.http
def main(request):
    aiplatform.init(project=PROJECT_ID, staging_bucket=BUCKET_NAME)

    compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path="test_train_pred.json",
    )

    pipeline_job = aiplatform.PipelineJob(
        display_name=RESOURCE_PREFIX + DISPLAY_NAME,
        template_path="test_train_pred.json",
        pipeline_root=PIPELINE_ROOT,
        enable_caching=False,
        parameter_values={
            'project': PROJECT_ID,
            'bucket': BUCKET_NAME,
            'predictor_repository': REPOSITORY,
            'endpoint_name': ENDPOINT_NAME,
            'region': REGION
        },
        project=PROJECT_ID
    )

    try:
        pipeline_job.run(
            service_account=SERVICE_ACCOUNT,
            sync=True
        )
    except Exception as e:
        return str(e), 500
    return "Success", 200
