import json

from apache_beam import (DoFn, GroupByKey, ParDo, Pipeline, PTransform,
                         WindowInto, WithKeys, io)
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.window import FixedWindows


class GroupMessagesByFixedWindows(PTransform):

    def __init__(self, window_size, num_shards=5):
        self.window_size = int(window_size * 60)
        self.num_shards = num_shards

    def expand(self, pcoll):
        import random
        return (
            pcoll
            | "Window into fixed intervals"
            >> WindowInto(FixedWindows(self.window_size))
            | "Add timestamp to windowed elements" >> ParDo(TransformMessage())
            # Assign a random key to each windowed element based on the number of shards.
            | "Add key" >> WithKeys(lambda _: random.randint(0, self.num_shards - 1))
            | "Group by key" >> GroupByKey()
        )


class TransformMessage(DoFn):
    def process(self, element, publish_time=DoFn.TimestampParam):
        from datetime import datetime
        ts = datetime.fromtimestamp(publish_time.seconds())
        data = dict(
            deviceId=element.attributes['deviceId'],
            year=ts.year,
            month=ts.month,
            day=ts.day,
            departament_id=None,
            product_id=None,
        )
        data.update(json.loads(element.data.decode('utf-8')))
        yield data


class WriteToGCS(DoFn):
    def __init__(self, output_path, output_format):
        self.output_path = output_path
        self.output_format = output_format

    def process(self, key_value, window=DoFn.WindowParam):
        """Write messages in a batch to Google Cloud Storage."""
        import pyarrow as pa
        import pyarrow.dataset as ds
        from gcsfs.core import GCSFileSystem
        ts_format = "%H:%M:%S"
        window_start = window.start.to_utc_datetime().strftime(ts_format)
        window_end = window.end.to_utc_datetime().strftime(ts_format)
        shard_id, batch = key_value
        table = pa.Table.from_pylist(batch)
        gcs = GCSFileSystem()
        if self.output_format == 'parquet':
            ds.write_dataset(
                data=table, base_dir=self.output_path,
                filesystem=gcs, format='parquet',
                partitioning=['departament_id',
                              'product_id', 'year', 'month', 'day'],
                basename_template=f'part_{window_start}-{window_end}_{shard_id}_{{i}}.parquet',
                partitioning_flavor='hive',
                existing_data_behavior='overwrite_or_ignore')
        if self.output_format == 'csv':
            ds.write_dataset(
                data=table, base_dir=self.output_path,
                filesystem=gcs, format='csv',
                partitioning=['departament_id',
                                       'product_id', 'year', 'month', 'day'],
                basename_template=f'part_{window_start}-{window_end}-{shard_id}_{{i}}.csv',
                partitioning_flavor='hive',
                existing_data_behavior='overwrite_or_ignore')


class JobOptions(PipelineOptions):
    @classmethod
    def _add_argparse_args(cls, parser):
        parser.add_argument(
            "--input_subscription",
            required=True,
            help="The Cloud Pub/Sub topic to read from."
            '"projects/<PROJECT_ID>/topics/<TOPIC_ID>".',
        )
        parser.add_argument(
            "--window_size",
            type=float,
            default=1.0,
            help="Output file's window size in minutes.",
        )
        parser.add_argument(
            "--output_path",
            required=True,
            help="Path of the output GCS file including the prefix.",
        )
        parser.add_argument(
            "--num_shards",
            type=int,
            default=1,
            help="Number of shards to use when writing windowed elements to GCS.",
        )
        parser.add_argument(
            "--output_format",
            default="csv",
            choices=["csv", "parquet"],
            help="Output files format.",
        )


def run():
    pipeline_options = PipelineOptions()
    job_options = pipeline_options.view_as(JobOptions)
    with Pipeline(options=pipeline_options) as pipeline:
        (
            pipeline
            | "Read from Pub/Sub" >> io.ReadFromPubSub(
                subscription=job_options.input_subscription, with_attributes=True)
            | "Window into" >> GroupMessagesByFixedWindows(job_options.window_size,
                                                           job_options.num_shards)
            | "Write to GCS" >> ParDo(WriteToGCS(job_options.output_path, job_options.output_format))
        )


if __name__ == "__main__":
    run()
