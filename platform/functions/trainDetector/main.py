import datetime
import logging
from os import environ
from sys import exit

from functions_framework import http as ff_http
from google.cloud import bigquery
from google.cloud.logging import Client as GCPLogClient


MODEL_FMT = "{project}.{dataset}.{model_prefix}{ver}"
TABLE_FMT = "{project}.{dataset}.{table_id}"
COPY_JOB_CONF = {
    "create_disposition": "CREATE_IF_NEEDED",
    "write_disposition": "WRITE_TRUNCATE",
}

QUERY_FMT = """
CREATE OR REPLACE MODEL `{model}`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='timestamp',
  TIME_SERIES_DATA_COL='value',
  HOLIDAY_REGION='US'
) AS
SELECT
  a.timestamp, a.value
FROM
  `{table}` a
"""


class BigQueryMLTrainer:

    def __init__(self, project_id: str, dataset: str, table_id: str, model_prefix:str):
        self.dt = datetime.datetime.now(tz=datetime.timezone.utc)
        self.project_id = project_id
        self.dataset = dataset
        self.model_prefix = model_prefix
        self.table_id = table_id
        self.bqclient = bigquery.Client()
        self.trained = False
        self.model_new = None
        self.model_latest = None

    def train_model(self) -> None:
        ver = self.dt.strftime('%Y%m%d')
        self.model_new = MODEL_FMT.format(project=self.project_id, dataset=self.dataset, model_prefix=self.model_prefix, ver=ver)
        table_full_name = TABLE_FMT.format(project=self.project_id, dataset=self.dataset, table_id=self.table_id)
        parametrized_query = QUERY_FMT.format(model=self.model_new, table=table_full_name)
        job = self.bqclient.query(parametrized_query) 
        job.result() # To wait untill query is finished
        self.trained = True
        logging.info(f"Model {self.model_new} was trained!")

    def replace_old(self) -> None:
        if not self.trained:
            logging.error("Trying to copy not created model")
            exit(1)
        self.model_latest = MODEL_FMT.format(project=self.project_id, dataset=self.dataset, model_prefix=self.model_prefix, ver='latest')
        self.bqclient.copy_table(sources=self.model_new, destination=self.model_latest, job_config=bigquery.CopyJobConfig(**COPY_JOB_CONF))
        logging.info(f"Model {self.model_latest} was updated to the latest version!")



@ff_http
def main(request):
    # Get Environment variables
    project_id = environ.get('project_id')
    dataset = environ.get('dataset')
    model_prefix = environ.get('model_prefix')
    table_id = environ.get('table_id')
    # Setting up Cloud logging
    client = GCPLogClient()
    client.setup_logging()
    # Training and updating the Anomaly Detection model
    trainer = BigQueryMLTrainer(project_id=project_id, dataset=dataset, table_id=table_id, model_prefix=model_prefix)
    trainer.train_model()
    trainer.replace_old()
    return 'Ok'
