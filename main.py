import json
import uuid
from functools import partial
from multiprocessing.pool import ThreadPool

import pika
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

import config
from analyser import Analyser
from logger import logger
from models import Base


def parse_message(uid, message):
    try:
        message = json.loads(message)
    except ValueError:
        logger.warning(f'[{uid}] Message not a valid json')
        return None

    required_keys = {'repo_id'}
    missing_keys = required_keys - set(message.keys())
    if missing_keys:
        logger.warning(f'[{uid}] Message incomplete, missing keys: [{", ".join(missing_keys)}]')
        return None

    return message


def process_incoming_message(db_conn, pool: ThreadPool, channel, method, properties, body):
    channel.stop_consuming()
    message = body.decode('utf-8')
    uid = str(uuid.uuid4())
    logger.info(f'[{uid}] Received message: {message}')
    message = parse_message(uid, message)

    if message is not None:
        # apply_async for multithreading - only if instant ACK is acceptable
        pool.apply(Analyser(uid, db_conn, message['repo_id']).analyse, [])
    else:
        logger.info(f'[{uid}] Skipping invalid message')

    channel.basic_ack(delivery_tag=method.delivery_tag)


engine = create_engine(config.DB_CONN_STRING)

try:
    logger.info(f"Connecting to RabbitMQ and database...")
    with pika.BlockingConnection(
            pika.ConnectionParameters(host=config.RABBITMQ_HOST, port=config.RABBITMQ_PORT)
        ) as rabbitmq_conn, engine.connect() as db_conn, ThreadPool(processes=4) as pool:
        logger.info('Connected')

        logger.info('Updating DB metadata...')
        Base.metadata.create_all(db_conn)
        logger.info('Done')

        in_channel = rabbitmq_conn.channel()
        in_channel.confirm_delivery()
        in_channel.queue_declare(queue=config.IN_QUEUE_NAME, durable=True)

        received_callback = partial(process_incoming_message, db_conn, pool)
        while True:
            in_channel.basic_consume(
                queue=config.IN_QUEUE_NAME,
                auto_ack=False,
                on_message_callback=received_callback
            )

            logger.info('Waiting for a message...')
            in_channel.start_consuming()

except pika.exceptions.AMQPConnectionError as e:
    logger.error(f"AMQP Connection Error: {e}")
except OperationalError as e:
    logger.error(f"DB Connection Error: {e}")
