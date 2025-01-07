#!/usr/bin/env bash
export UNINGESTED_PATH='uningested'
export BUCKET='ap-developer-vectors-bucket'
export CHOICE='ingest'

DIR_TO_INGEST="example"

aws s3 cp $DIR_TO_INGEST s3://$BUCKET/$UNINGESTED_PATH/$DIR_TO_INGEST --recursive
cd docker
source scripts/set_oai_vars.sh
export EMBEDDING_SUMMARIZE=true
python app/main.py $CHOICE