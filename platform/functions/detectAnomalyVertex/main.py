import logging

from base64 import b64decode, b64encode
from json import loads, dumps
from os import environ

from google.cloud import aiplatform
from google.cloud import bigquery
from google.cloud.iot_v1 import DeviceManagerClient
from google.cloud.logging import Client as GCPLogClient
from pandas import DataFrame, Series, concat, to_datetime
from device_communicator import DeviceCommunicator


DESTINATION_TABLE_FMT = "{project}.{dataset}.{destination_table}"
COMMAND_FMT = "Found high anomaly at {timestamp}: {value}"
PREVIOUS_ROWS_QUERY_FMT = """
SELECT a.timestamp, a.value
    FROM `{project}.{dataset}.{table_id}` a
   WHERE a.timestamp >= datetime_sub(timestamp("{timestamp}"), INTERVAL {interval} SECOND)
     AND a.timestamp < timestamp("{timestamp}")
ORDER BY a.timestamp
"""


def serialize_pd(series: Series):
    obj = {
        'timestamp': str(series.index[-1]),
        'values': series.to_json()
    }
    b64_encoded = b64encode(dumps(obj).encode('utf-8'))
    return [{"data": {"b64": b64_encoded.decode('utf-8')}}]


class PubSubDataProcessor:

    def __init__(self, project_id: str, cloud_region: str, registry_id: str, device_id: str, period: int,
                       dataset: str, endpoint_name: str, input_size: int, table_id: str, destination_table: str):
        self.project_id = project_id
        self.cloud_region = cloud_region
        self.registry_id = registry_id
        self.device_id = device_id
        self.dataset = dataset
        self.input_size = input_size
        self.table_id = table_id
        self.period = period
        self.destination_table = destination_table
        self.device_com = None
        self.dm_client = None
        
        self._set_endpoint(endpoint_name)
        self.bqclient = bigquery.Client()

    def detect_anomaly(self, timestamp, value):
        query = PREVIOUS_ROWS_QUERY_FMT.format(
            dataset=self.dataset,
            interval=self.input_size * self.period,
            timestamp=timestamp,
            table_id=self.table_id,
            project=self.project_id
        )
        inputs = self.bqclient.query(query).result().to_dataframe()
        if len(inputs) != self.input_size:
            error_message = 'Not correct number of points before to detect an outlier: ' \
                            f'{len(inputs)} provided while {self.input_size} needed'
            logging.error(error_message)
            raise ValueError(f"Can't get the predictions due to the error:\n{error_message}")
        inputs = concat([inputs, DataFrame({
            'value': [value],
            'timestamp': [timestamp]}
        )], axis=0, ignore_index=True)
        inputs['timestamp'] = to_datetime(inputs['timestamp'], utc=True)
        inputs.set_index('timestamp', inplace=True)
        inputs = inputs.sort_index()
        inputs = inputs['value']
        return self.is_anomaly(inputs)

    def _set_endpoint(self, endpoint_name):
        filter = f'display_name="{endpoint_name}"'
        endpoint_info = None
        for endpoint_info in aiplatform.Endpoint.list(filter=filter):
            print(f"Endpoint display name = {endpoint_info.display_name} resource id = {endpoint_info.resource_name}")
        
        if endpoint_info is None:
            raise ValueError(f"There is no endpoint `{endpoint_name}`")
        else:
            self.endpoint = aiplatform.Endpoint(endpoint_info.resource_name)

    def is_anomaly(self, inputs: Series):
        serialized = serialize_pd(inputs)
        prediction = self.endpoint.predict(instances=serialized)
        prediction = prediction.predictions[0]
        is_anomaly, _, real, lower_bound, upper_bound = prediction
        is_anomaly = is_anomaly != 0
        row = DataFrame({
            'timestamp': [str(inputs.index[-1])],
            'is_anomaly':[is_anomaly],
            'value':[real],
            'upper_bound':[upper_bound],
            'lower_bound':[lower_bound],
        }).iloc[0]
        return row, is_anomaly

    def populate_vis_table(self, row):
        destination_table_full_name = DESTINATION_TABLE_FMT.format(
            project=self.project_id, 
            dataset=self.dataset, 
            destination_table=self.destination_table)
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
    device_id = event['attributes']['deviceId']
    registry_id = environ.get('registry_id')
    dataset = environ.get('dataset')
    endpoint_name = environ.get('endpoint_name')
    input_size = int(environ.get('input_size'))
    period = int(environ.get('period'))
    table_id = environ.get('table_id')
    destination_table = environ.get('destination_table')
    #Setting up Cloud and initializing the processor
    client = GCPLogClient()
    client.setup_logging()
    aiplatform.init(project=project_id)

    processor = PubSubDataProcessor(
        project_id=project_id,
        cloud_region=cloud_region,
        registry_id=registry_id,
        device_id=device_id,
        dataset=dataset,
        input_size=input_size,
        period=period,
        endpoint_name=endpoint_name,
        destination_table=destination_table,
        table_id=table_id,
    )
    # Extracting IoT data
    data = loads(b64decode(event['data']).decode('utf-8'))
    timestamp = data['timestamp']
    value = data['value']

    # Detect anomalies
    anomaly_row, is_anomaly = processor.detect_anomaly(timestamp, value)
    logging.info(f"{is_anomaly}: {anomaly_row}")
    # Populating visualization table
    processor.populate_vis_table(anomaly_row)
    # If anomaly is detected, send the feedback
    if is_anomaly is not None and is_anomaly:
        processor.feedback_to_device(anomaly_row)
