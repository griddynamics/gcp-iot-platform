#!/bin/bash -e

cd ${1}/functions
for dir in * ; do
    cd $dir
    zip $dir.zip *
    gsutil cp $dir.zip ${2}/functions/
    cd ../
done
