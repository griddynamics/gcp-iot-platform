import datetime
import json
import logging
import random
import ssl
import time
from json.decoder import JSONDecodeError
from typing import Dict, Sequence

import jwt
import paho.mqtt.client as mqtt


class Client():

    def __init__(self, *,
                 project_id: str,
                 location: str,
                 registry_id: str,
                 device_id: str,
                 private_key_file: str,
                 algorithm: str = 'RS256',
                 ca_certs: str,
                 mqtt_bridge_hostname: str = 'mqtt.googleapis.com',
                 mqtt_bridge_port: int = 8883,
                 maximum_backoff_time: int = 32,
                 events_sub_topic: str = 'events',
                 jwt_expires_minutes: int = 20,
                 use_input_timestamp: bool = False,
                 input_ts_format: str = '%Y-%m-%d %H:%M:%S',
                 output_ts_format: str = '%Y-%m-%dT%H:%M:%S',
                 **kwargs
                 ) -> None:
        self.project_id = project_id
        self.location = location
        self.registry_id = registry_id
        self.device_id = device_id
        self.private_key_file = private_key_file
        self.algorithm = algorithm
        self.ca_certs = ca_certs
        self.mqtt_bridge_hostname = mqtt_bridge_hostname
        self.mqtt_bridge_port = mqtt_bridge_port
        self.should_backoff = False
        self.minimum_backoff_time = 1
        self.maximum_backoff_time = maximum_backoff_time
        self.events_topic = f'/devices/{device_id}/{events_sub_topic}'
        self.state_topic = f'/devices/{device_id}/state'
        self.jwt_expires_minutes = jwt_expires_minutes
        self.use_input_timestamp = use_input_timestamp
        self.input_ts_format = input_ts_format
        self.output_ts_format = output_ts_format
        self.init_state()

    def init_state(self):
        self.state = {'enabled': True}

    def update_state(self, config):
        self.state.update(config)

    def create_jwt(self, project_id, private_key_file, algorithm):
        """Creates a JWT (https://jwt.io) to establish an MQTT connection."""
        token = {
            "iat": datetime.datetime.now(tz=datetime.timezone.utc),
            "exp": datetime.datetime.now(
                tz=datetime.timezone.utc) + datetime.timedelta(minutes=20),
            "aud": project_id,
        }
        with open(private_key_file, "r") as f:
            private_key = f.read()
        logging.info(
            "Creating JWT using {} from private key file {}".format(
                algorithm, private_key_file
            )
        )
        return jwt.encode(token, private_key, algorithm=algorithm)

    def error_str(self, rc):
        """Convert a Paho error to a human readable string."""
        return "{}: {}".format(rc, mqtt.error_string(rc))

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when a device connects."""
        logging.info(f"on_connect {mqtt.connack_string(rc)}")
        self.should_backoff = False
        self.minimum_backoff_time = 1

    def on_disconnect(self, client, userdata, rc):
        """Paho callback for when a device disconnects."""
        logging.info(f"on_disconnect {self.error_str(rc)}")
        self.should_backoff = True

    def on_publish(self, unused_client, unused_userdata, unused_mid):
        """Paho callback when a message is sent to the broker."""
        logging.debug("on_publish")

    def on_config_message(self, client, userdata, message):
        """Callback when the device receives a config message on a subscription."""
        payload = str(message.payload.decode("utf-8"))
        logging.info(f"Received config message '{payload}'"
                     f" on topic '{message.topic}' with Qos {message.qos}")
        try:
            new_config = json.loads(payload)
            self.update_state(config=new_config)
            client.publish(self.state_topic, json.dumps(self.state), qos=1)
        except JSONDecodeError as e:
            logging.warning(f'Config message is incorrect: {e}')

    def on_message(self, client, userdata, message):
        """Callback when the device receives a message on a subscription."""
        payload = str(message.payload.decode("utf-8"))
        logging.info(f"Received message '{payload}'"
                     f" on topic '{message.topic}' with Qos {message.qos}")

    def get_client(self):
        """Create MQTT client."""
        client_id = (f'projects/{self.project_id}/locations/{self.location}/'
                     f'registries/{self.registry_id}/devices/{self.device_id}')
        logging.info("Device client_id is '{}'".format(client_id))
        client = mqtt.Client(client_id=client_id)
        client.username_pw_set(
            username='unused',
            password=self.create_jwt(self.project_id, self.private_key_file,
                                     self.algorithm))
        client.tls_set(ca_certs=self.ca_certs,
                       tls_version=ssl.PROTOCOL_TLSv1_2)
        mqtt_config_topic = "/devices/{}/config".format(self.device_id)
        mqtt_command_topic = "/devices/{}/commands/#".format(self.device_id)
        client.on_connect = self.on_connect
        client.on_publish = self.on_publish
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message
        client.message_callback_add(mqtt_config_topic,
                                    self.on_config_message)
        client.connect(self.mqtt_bridge_hostname, self.mqtt_bridge_port)
        client.subscribe(mqtt_config_topic, qos=1)
        client.subscribe(mqtt_command_topic, qos=0)
        return client

    def get_payload(self, value: Dict):
        if self.use_input_timestamp:
            timestamp = time.strftime(
                self.output_ts_format,
                time.strptime(value['timestamp'],
                              self.input_ts_format))
        else:
            timestamp = datetime.datetime.now(
                tz=datetime.timezone.utc).strftime(self.output_ts_format)
        payload = json.dumps({
            'timestamp': timestamp,
            'value': value['value']})
        return payload

    def mqtt_device_run(self, values: Sequence[Dict]):
        """Connects a device, sends data loop, and receives data."""
        jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
        client = self.get_client()
        client.loop_start()
        time.sleep(10)
        while self.state['enabled']:
            for value in values:
                if not self.state['enabled']:
                    break
                # Wait if backoff is required.
                if self.should_backoff:
                    # If backoff time is too large, give up.
                    if self.minimum_backoff_time > self.maximum_backoff_time:
                        logging.warning(
                            "Exceeded maximum backoff time. Giving up.")
                        break
                    # Otherwise, wait and connect again.
                    delay = self.minimum_backoff_time + \
                        random.randint(0, 1000) / 1000.0
                    logging.info(
                        "Waiting for {} before reconnecting.".format(delay))
                    time.sleep(delay)
                    self.minimum_backoff_time *= 2
                    client.reconnect()
                payload = self.get_payload(value)
                logging.info("Publishing message: '{}'".format(payload))
                seconds_since_issue = (datetime.datetime.now(
                    tz=datetime.timezone.utc) - jwt_iat).seconds
                if seconds_since_issue > 60 * self.jwt_expires_minutes:
                    logging.info("Refreshing token after {}s".format(
                        seconds_since_issue))
                    jwt_iat = datetime.datetime.now(tz=datetime.timezone.utc)
                    client.loop_stop()
                    client.disconnect()
                    client = self.get_client()
                    client.loop_start()
                client.publish(self.events_topic, payload, qos=1)
                time.sleep(60)
        client.loop_stop()
