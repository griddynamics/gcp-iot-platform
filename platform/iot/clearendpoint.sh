#!/bin/bash -e
id=$(gcloud ai endpoints list --region ${1} | grep ${2} | awk '{ print $1 }') && \
model=$(gcloud ai endpoints describe $id --region ${1} | grep "id" | awk '{ print $2 }' | sed "s/'//g")
for x in $model;
do gcloud ai endpoints undeploy-model $id --region ${1} --deployed-model-id $x;
done
gcloud ai endpoints delete $id --region ${1} --quiet
