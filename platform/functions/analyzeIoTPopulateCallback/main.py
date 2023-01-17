import logging

from base64 import b64decode
from json import loads, dumps
from os import environ

from google.api_core.exceptions import FailedPrecondition
from google.cloud import bigquery
from google.cloud.iot_v1 import DeviceManagerClient
from google.cloud.logging import Client as GCPLogClient
from pandas._libs.missing import NAType

MODEL_FMT = "{}.{}.{}latest"
DESTINATION_TABLE_FMT = "{}.{}.{}"
THRESHOLD = environ.get('THRESHOLD', 0.95)
COMMAND_FMT = "Found high anomaly at {timestamp}: {value}"

QUERY_FMT = """
SELECT timestamp, is_anomaly, value, lower_bound, upper_bound, anomaly_probability FROM ML.DETECT_ANOMALIES(
    MODEL `{model}`, 
    STRUCT({threshold} AS anomaly_prob_threshold),
    ( SELECT TIMESTAMP("{timestamp}") timestamp, {value} value )
)
"""


class DeviceCommunicator():

    def __init__(self, client: DeviceManagerClient, project_id: str, cloud_region: str, registry_id: str,
                 device_id: str, version: str = "0") -> None:
        self.client: DeviceManagerClient = client
        self.project_id = project_id
        self.cloud_region = cloud_region
        self.registry_id = registry_id
        self.device_id = device_id
        self.version = version

    def set_config(self, config: str):
        device_path = self.client.device_path(
            self.project_id, self.cloud_region, self.registry_id, self.device_id)
        data = config.encode("utf-8")
        try:
            self.client.modify_cloud_to_device_config(
                request={"name": device_path, "binary_data": data,
                         "version_to_update": self.version})
        except FailedPrecondition as e:
            logging.error(e)

    def send_command(self, command: str):
        device_path = self.client.device_path(
            self.project_id, self.cloud_region, self.registry_id, self.device_id)
        data = command.encode("utf-8")
        try:
            return self.client.send_command_to_device(
                request={"name": device_path, "binary_data": data}
            )
        except FailedPrecondition as e:
            logging.error(e)


class PubSubDataProcessor:

    def __init__(self, project_id: str, cloud_region: str, registry_id: str, device_id: str,
                       dataset: str, model_prefix: str, destination_table: str):
        self.project_id = project_id
        self.cloud_region = cloud_region
        self.registry_id = registry_id
        self.device_id = device_id
        self.dataset = dataset
        self.model_prefix = model_prefix
        self.destination_table = destination_table
        self.device_com = None
        self.dm_client = None

        self.bqclient = bigquery.Client()

    def detect_anomaly(self, timestamp, value):
        full_model_name = MODEL_FMT.format(self.project_id, self.dataset, self.model_prefix)
        parametrized_query = QUERY_FMT.format(
            model=full_model_name,
            threshold=THRESHOLD,
            value=value,
            timestamp=timestamp
        )
        job = self.bqclient.query(parametrized_query)
        row = job.result().to_dataframe()
        row['timestamp'] = row['timestamp'].map(str)
        row = row.iloc[0]
        is_anomaly = PubSubDataProcessor.is_anomaly(row)
        return row, is_anomaly

    @staticmethod
    def is_anomaly(row):
        if isinstance(row['is_anomaly'], NAType):
            # if model is not outputting results:
            logging.warning("No prediction!!!")
            return None
        return row["is_anomaly"]

    def populate_vis_table(self, row):
        destination_table_full_name = DESTINATION_TABLE_FMT.format(self.project_id, self.dataset, self.destination_table)
        errors = self.bqclient.insert_rows_json(destination_table_full_name, [row.dropna().to_dict()])
        if errors == []:
            logging.info("New rows have been added.")
        else:
            logging.error(
                "Encountered errors while inserting rows: {}".format(errors))

    def set_device_communicator(self):
        if self.device_com is None:
            self.client = DeviceManagerClient()
            self.device_com = DeviceCommunicator(
                client=self.client,
                project_id=self.project_id,
                cloud_region=self.cloud_region,
                registry_id=self.registry_id,
                device_id=self.device_id
            )

    def feedback_to_device(self, anomaly_detection_result):
        if self.device_com is None:
            self.set_device_communicator()

        if anomaly_detection_result['value'] > anomaly_detection_result["upper_bound"]:
            command = COMMAND_FMT.format(
                timestamp=anomaly_detection_result['timestamp'],
                value=anomaly_detection_result['value']
            )
            self.device_com.send_command(command=command)
            logging.info(f"Command sent: {command}")
        elif anomaly_detection_result['value'] < anomaly_detection_result["lower_bound"]:
            turn_off_config = dumps({'enabled': False})
            self.device_com.set_config(config=turn_off_config)
            logging.info(f"Config was changed: {turn_off_config}")



def main(event, context):
    # Get Environment variables
    project_id = environ.get('project_id')
    cloud_region = environ.get('cloud_region')
    registry_id = environ.get('registry_id')
    dataset = environ.get('dataset')
    model_prefix = environ.get('model_prefix')
    destination_table = environ.get('destination_table')
    device_id = event['attributes']['deviceId']
    #Setting up Cloud logging and initializing the processor
    client = GCPLogClient()
    client.setup_logging()

    processor = PubSubDataProcessor(
        project_id=project_id,
        cloud_region=cloud_region,
        registry_id=registry_id,
        device_id=device_id,
        dataset=dataset,
        model_prefix=model_prefix,
        destination_table=destination_table
    )
    # Extracting IoT data
    data = loads(b64decode(event['data']).decode('utf-8'))
    timestamp = data['timestamp']
    value = data['value']

    # Detect anomalies
    anomaly_row, is_anomaly = processor.detect_anomaly(timestamp, value)
    # Populating visualization table
    processor.populate_vis_table(anomaly_row)
    # If anomaly is detected, send the feedback
    if is_anomaly is not None and is_anomaly:
        processor.feedback_to_device(anomaly_row)
