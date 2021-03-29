#!/usr/bin/env python3
import os

from flask import Flask
from google.cloud import pubsub_v1
from google.cloud import storage

app = Flask(__name__)
gcs_client = storage.Client()
app.config['PUBSUB_VERIFICATION_TOKEN'] = \
    os.environ['PUBSUB_VERIFICATION_TOKEN']
app.config['PUBSUB_TOPIC'] = os.environ['PUBSUB_TOPIC']
app.config['PUB_TOPIC'] = os.environ['PUB_TOPIC']
app.config['GOOGLE_CLOUD_PROJECT'] = os.environ['GOOGLE_CLOUD_PROJECT']
app.config['CLOUD_STORAGE_BUCKET'] = os.environ['CLOUD_STORAGE_BUCKET']

app.config['FOLDER_NAME'] = os.environ.get("FOLDER_NAME", "test-data")

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

gcs_client = storage.Client()
bucket = gcs_client.get_bucket(app.config['CLOUD_STORAGE_BUCKET'])
publisher = pubsub_v1.PublisherClient()
