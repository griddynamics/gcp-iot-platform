import argparse
import csv
import logging
from io import StringIO

import google.cloud.logging
from google.cloud import compute_v1, storage

from client import Client


def parse_command_line_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--algorithm", choices=("RS256", "ES256"),
        help="Which encryption algorithm to use to generate the JWT", default="${algorithm}")
    parser.add_argument(
        "--ca_certs", default="root.pem",
        help="CA root from https://pki.google.com/roots.pem")
    parser.add_argument(
        "--device_id", help="Cloud IoT Core device id", default="${device_id}")
    parser.add_argument(
        "--jwt_expires_minutes", default=20, type=int,
        help="Expiration time, in minutes, for JWT tokens")
    parser.add_argument(
        "--location", help="GCP IoT Core region", default="${region}")
    parser.add_argument(
        "--mqtt_bridge_hostname", default="mqtt.googleapis.com",
        help="MQTT bridge hostname.")
    parser.add_argument(
        "--mqtt_bridge_port", choices=(8883, 443), default=8883, type=int,
        help="MQTT bridge port")
    parser.add_argument(
        "--private_key_file", default="private_key.pem",
        help="Path to private key file")
    parser.add_argument(
        "--project_id", help="GCP cloud project name", default="${project_id}")
    parser.add_argument(
        "--gce_zone", help="VM instance zone", default="${zone}")
    parser.add_argument(
        "--gce_instance", help="VM instance name", default="${mqtt_client}")
    parser.add_argument(
        "--registry_id", help="Registry ID", default="${registry_id}")
    parser.add_argument(
        "--maximum_backoff_time", default=32, type=int,
        help="Maximum backoff time")
    parser.add_argument(
        "--events_sub_topic", default="events", help="Events sub topic")
    parser.add_argument(
        "--events_data_bucket", help="Events data GCS bucket", default="${bucket}")
    parser.add_argument(
        "--events_data_blob", help="Events data GCS blob", default="data/device_new_data.csv")
    parser.add_argument(
        "--use_input_timestamp", action='store_true',
        help="Use timestamp from file or device timestamp")
    parser.add_argument(
        "--input_ts_format", default="%Y-%m-%d %H:%M:%S",
        help="Input file timestamp format")
    parser.add_argument(
        "--output_ts_format", default="%Y-%m-%dT%H:%M:%S",
        help="Output timestamp format")
    return parser.parse_args()


def main():
    log_client = google.cloud.logging.Client()
    log_client.setup_logging()
    logging.getLogger().setLevel(logging.INFO)
    arg_parser = parse_command_line_args()
    events_text_file: str = (storage.Client()
                             .bucket(arg_parser.events_data_bucket)
                             .blob(arg_parser.events_data_blob)
                             .download_as_text())
    values = list(csv.DictReader(StringIO(events_text_file)))
    mqtt_client = Client(**vars(arg_parser))
    mqtt_client.mqtt_device_run(values=values)
    logging.info("Finished.")
    compute_v1.InstancesClient().stop(project=arg_parser.project_id,
                                      zone=arg_parser.gce_zone,
                                      instance=arg_parser.gce_instance)


if __name__ == "__main__":
    main()
