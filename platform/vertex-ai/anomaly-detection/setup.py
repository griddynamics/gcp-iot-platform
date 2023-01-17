from setuptools import find_packages
from setuptools import setup

REQUIRED_PACKAGES = [
    # Not including the commented dependencies, as this library is supposed to run on the 
    # pre-build docker images for GCP VertexAI Training, where they are already installed
    # 'google-cloud-bigquery==3.2.0',
    # 'google-cloud-logging==3.2.1',
    # 'google-cloud-storage==3.2.0',
    # 'torch=1.12.1',
    # 'numpy==1.21.5'
    'pandas==1.3.5',
    'fsspec==2022.8.2',
    'gcsfs==2022.8.2']


setup(
    name='ts-anomaly-detection-trainer',
    version='0.1.1',
    install_requires=REQUIRED_PACKAGES,
    packages=find_packages(),
    include_package_data=True,
    description='Anomaly detection training package compatible with GCP VertexAI Training Jobs pre-build images'
)
