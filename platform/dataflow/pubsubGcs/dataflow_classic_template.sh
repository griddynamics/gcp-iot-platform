#!/bin/bash -e

python3 -m venv ${1}/venv && source ${1}/venv/bin/activate && \
pip3 install --upgrade pip && pip3 install -r ${1}/requirements.txt && \
python3 ${1}/pubsub_to_gcs.py --runner DataflowRunner --project ${2} --staging_location ${3}/staging \
--temp_location ${3}/temp --template_location ${3}/templates/iot-pubsub-gcs --streaming --region ${4} --input_subscription \
${5} --output_path ${6}/output --service_account_email ${7} --save_main_session --max_num_workers 1 \
--requirements_file ${1}/requirements.txt && deactivate && rm -r ${1}/venv
