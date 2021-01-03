import json
import logging
import uuid
from functools import partial
from multiprocessing.pool import ThreadPool

import pika
from radon.raw import analyze
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

import config
from models import PythonFile, PythonRepo, Base

LANGUAGE_ID = 8


def analyse(uid, db_conn, repo_id, files):
    try:
        logger.info(f'Started processing of a message [{uid}]')
        session = sessionmaker(bind=db_conn)()

        agg_stats = {}
        for file in files:
            with open(file, 'r') as f:
                stats = analyze(f.read())
                agg_stats[file] = stats
                print(stats)

        save_stats(session, repo_id, agg_stats)
        send_ack(repo_id)
        logger.info(f'Message [{uid}] processed successfully')
    except Exception as e:
        logger.exception(f'Exception occurred during processing message [{uid}]: {e}')


def save_stats(session, repo_id, agg_stats):
    repo = PythonRepo(repo_id=repo_id)
    session.add(repo)

    for file, stats in agg_stats.items():
        python_file = PythonFile(repo=repo, name=file, **stats._asdict())

        session.add(python_file)

    session.commit()


def send_ack(repo_id):
    queue_name = 'gc'
    msg = {
        'repo_id': repo_id,
        'language_id': LANGUAGE_ID,
    }
    send_to_queue(queue_name, msg)


def send_to_queue(queue_name, msg):
    return
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name)
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=json.dumps(msg))


def parse_message(uid, message):
    try:
        message = json.loads(message)
    except ValueError:
        logger.warning(f'Message [{uid}] not a valid json')
        return None

    required_keys = {'repo_id'}
    missing_keys = required_keys - set(message.keys())
    if missing_keys:
        logger.warning(f'Message [{uid}] incomplete, missing keys: [{", ".join(missing_keys)}]')
        return None

    return message


def process_incoming_message(db_conn, pool: ThreadPool, channel, method, properties, body):
    channel.stop_consuming()
    message = body.decode('utf-8')
    uid = str(uuid.uuid4())
    logger.info(f'Received message: [{uid}] {message}')
    message = parse_message(uid, message)

    if message is not None:
        pool.apply_async(analyse, [uid, db_conn, message['repo_id'], ['main.py']])
    else:
        logger.info(f'Skipping invalid message [{uid}')

    channel.basic_ack(delivery_tag=method.delivery_tag)


engine = create_engine(config.DB_CONN_STRING)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

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
