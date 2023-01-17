import logging
from typing import Optional

from google.api_core.exceptions import FailedPrecondition
from google.cloud.iot_v1 import DeviceManagerClient


class DeviceCommunicator():

    def __init__(self, client: Optional[DeviceManagerClient], project_id: str, cloud_region: str, registry_id: str,
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
