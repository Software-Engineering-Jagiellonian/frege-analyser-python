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
from models import PythonFile, RepositoryLanguage, Base


class Analyser:
    LANGUAGE_ID = 8

    def __init__(self, uid, db_conn, repo_id):
        self.uid = uid
        self.db_conn = db_conn
        self.repo_id = repo_id
        self.repo = None
        self.out_channel = None

    def analyse(self):
        try:
            logger.info(f'[{self.uid}] Started processing of the message')

            session = sessionmaker(bind=db_conn)()
            self.repo = session.query(RepositoryLanguage).filter(
                RepositoryLanguage.repository_id == self.repo_id,
                RepositoryLanguage.language_id == self.LANGUAGE_ID
            ).first()
            if not self.repo:
                raise Exception('No repository entity found')

            self.out_channel = pika.BlockingConnection(
                pika.ConnectionParameters(host=config.RABBITMQ_HOST, port=config.RABBITMQ_PORT)
            ).channel()
            self.out_channel.confirm_delivery()
            self.out_channel.queue_declare(queue=config.OUT_QUEUE_NAME, durable=True)

            agg_stats = {}
            for file in self.repo.files:
                with open(file.file_path, 'r') as f:
                    stats = analyze(f.read())
                    agg_stats[file.id] = stats
                    print(stats)

            self.save_stats(session, agg_stats)
            self.send_ack()
            logger.info(f'[{self.uid}] Message processed successfully')
        except Exception as e:
            logger.exception(f'[{self.uid}] Exception occurred during processing of the message: {e}')

    def save_stats(self, session, agg_stats):
        for file, stats in agg_stats.items():
            python_file = PythonFile(file_id=file, **stats._asdict())

            session.add(python_file)

        session.commit()

    def send_ack(self):
        msg = {
            'repo_id': self.repo_id,
            'language_id': self.LANGUAGE_ID,
        }
        self.send_to_queue(msg)

    def send_to_queue(self, msg):
        queue_name = config.OUT_QUEUE_NAME
        try:
            self.out_channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                properties=pika.BasicProperties(delivery_mode=2),
                body=json.dumps(msg).encode('utf-8')
            )
            logger.info(f'[{self.uid}] Message to the {queue_name} queue was received by RabbitMQ')
        except pika.exceptions.NackError:
            logger.exception(f'[{self.uid}] Message to the {queue_name} queue was rejected by RabbitMQ')


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
