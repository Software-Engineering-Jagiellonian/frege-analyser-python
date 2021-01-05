import os

DB_HOST = os.environ['DB_HOST']
DB_PORT = int(os.environ['DB_PORT'])
DB_USER = os.environ['DB_USERNAME']
DB_PASS = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_DATABASE']
DB_CONN_STRING = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

RABBITMQ_HOST = os.environ['RMQ_HOST']
RABBITMQ_PORT = int(os.environ['RMQ_PORT'])

IN_QUEUE_NAME = 'analyze-python'
OUT_QUEUE_NAME = 'gc'

PUBLISH_DELAY = os.environ['RMQ_REJECTED_PUBLISH_DELAY']
