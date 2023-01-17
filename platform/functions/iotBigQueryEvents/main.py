import base64
import json
import logging
import os
from datetime import datetime

import google.cloud.logging
from google.cloud import bigquery


def iot_events_to_bq(event, context):
    log_client = google.cloud.logging.Client()
    log_client.setup_logging()
    data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
    DATE_POINT = os.environ.get('date_point', '2011-08-03T23:25:01')
    INTERVAL_SEC = int(os.environ.get('interval_sec', 60))
    TS_FORMAT = os.environ.get('ts_format', '%Y-%m-%dT%H:%M:%S')
    ts_point = datetime.strptime(DATE_POINT, TS_FORMAT).timestamp()
    ts_input = datetime.strptime(data['timestamp'], TS_FORMAT).timestamp()
    # round timestamp to (date_point+N*interval_sec) value
    ts = (ts_input - ts_point) // INTERVAL_SEC * INTERVAL_SEC + ts_point
    rows = [{'timestamp': datetime.fromtimestamp(ts).strftime(TS_FORMAT),
             'value': data['value'],
             'deviceId': event['attributes']['deviceId']}]
    bq_client = bigquery.Client()
    PROJECT_ID = os.environ.get('project_id')
    DATASET = os.environ.get('dataset')
    TABLE = os.environ.get('table_id')
    table_id = f'{PROJECT_ID}.{DATASET}.{TABLE}'
    errors = bq_client.insert_rows_json(table_id, rows)
    if errors == []:
        logging.info('New rows have been added.')
    else:
        logging.warning(
            'Encountered errors while inserting rows: {}'.format(errors))
